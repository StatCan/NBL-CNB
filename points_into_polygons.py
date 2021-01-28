import geopandas as gpd
import logging
import numpy as np
import os
import pandas as pd
import re
import shapely
import sys
from bisect import bisect
from collections import OrderedDict
from operator import add, itemgetter
from shapely.geometry import Point

sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers

#-------------------------------------------------------------------------------------------------------------------
# Functions

def groupby_to_list(df, group_field, list_field):
    """
    Helper function: faster alternative to pandas groupby.apply/agg(list).
    Groups records by one or more fields and compiles an output field into a list for each group.
    """
    
    if isinstance(group_field, list):
        for field in group_field:
            if df[field].dtype.name != "geometry":
                df[field] = df[field].astype("U")
        transpose = df.sort_values(group_field)[[*group_field, list_field]].values.T
        keys, vals = np.column_stack(transpose[:-1]), transpose[-1]
        keys_unique, keys_indexes = np.unique(keys.astype("U") if isinstance(keys, np.object) else keys, 
                                              axis=0, return_index=True)
    
    else:
        keys, vals = df.sort_values(group_field)[[group_field, list_field]].values.T
        keys_unique, keys_indexes = np.unique(keys, return_index=True)
    
    vals_arrays = np.split(vals, keys_indexes[1:])
    
    return pd.Series([list(vals_array) for vals_array in vals_arrays], index=keys_unique).copy(deep=True)

def as_int(val):
    "Step 2: Converts linkages to integer tuples, if possible"
    try:
        return int(val)
    except ValueError:
        return val

def get_nearest_linkage(pt, roadseg_indexes):
    """Returns the roadseg index associated with the nearest roadseg geometry to the given address point."""
    
    # Get roadseg geometries.
    roadseg_geometries = tuple(map(lambda index: roadseg["geometry"].iloc[index], roadseg_indexes))
    
    # Get roadseg distances from address point.
    roadseg_distances = tuple(map(lambda road: pt.distance(road), roadseg_geometries))
    
    # Get the roadseg index associated with the smallest distance.
    roadseg_index = roadseg_indexes[roadseg_distances.index(min(roadseg_distances))]
    
    return roadseg_index

# ---------------------------------------------------------------------------------------------------------------
# Inputs

# Define index of example roadseg segment.
ex_idx = 264
ex_place = "City of Yellowknife"

# Layer inputs
project_gpkg = "H:/point_to_polygon_PoC/data/data.gpkg"
addresses_lyr_nme = "yk_Address_Points"
bf_lyr_nme = "yk_buildings_sj"

# ---------------------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
addresses = gpd.read_file(project_gpkg, layer= addresses_lyr_nme)
roadseg = gpd.read_file(project_gpkg, layer= bf_lyr_nme) # spatial join between the parcels and building footprints layers

# Clean data
# Remove rite of way from the address data and join count > 0
addresses = addresses[(addresses.CIVIC_ADDRESS != "RITE OF WAY")]

# Remove null street name rows
roadseg = roadseg[(roadseg.Join_Count > 0) & (roadseg.STREET_NAME.notnull()) & (roadseg.STREET_NAME != ' ')] 

print( "Running Step 1. Load dataframes and configure attributes")
# Define join fields.
join_roadseg = "STREET_NAME"
join_addresses = "STREET_NAME"

# Configure attributes - number and suffix.
addresses["suffix"] = addresses["CIVIC_ADDRESS"].map(lambda val: re.sub(pattern="\\d+", repl="", string=val, flags=re.I))
addresses["number"] = addresses["CIVIC_ADDRESS"].map(lambda val: re.sub(pattern="[^\\d]", repl="", string=val, flags=re.I)).map(int)

print("Running Step 2. Configure address to roadseg linkages")
# Link addresses and roadseg on join fields.
addresses["addresses_index"] = addresses.index
roadseg["roadseg_index"] = roadseg.index

merge = addresses.merge(roadseg[[join_roadseg, "roadseg_index"]], how="left", left_on=join_addresses, right_on=join_roadseg)
addresses["roadseg_index"] = groupby_to_list(merge, "addresses_index", "roadseg_index")

addresses.drop(columns=["addresses_index"], inplace=True)
roadseg.drop(columns=["roadseg_index"], inplace=True)

# Discard non-linked addresses.
addresses.drop(addresses[addresses["roadseg_index"].map(itemgetter(0)).isna()].index, axis=0, inplace=True)

# Convert linkages to integer tuples, if possible.

addresses["roadseg_index"] = addresses["roadseg_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = addresses["roadseg_index"].map(len) > 1

# Reduce plural linkages to the road segment with the lowest (nearest) geometric distance.
addresses.loc[flag_plural, "roadseg_index"] = addresses[flag_plural][["geometry", "roadseg_index"]].apply(
    lambda row: get_nearest_linkage(*row), axis=1)

# Unpack first tuple element for singular linkages.
addresses.loc[~flag_plural, "roadseg_index"] = addresses[~flag_plural]["roadseg_index"].map(itemgetter(0))

# Compile linked roadseg geometry for each address.
addresses["roadseg_geometry"] = addresses.merge(
    roadseg["geometry"], how="left", left_on="roadseg_index", right_index=True)["geometry_y"]

print(addresses.head())

print('DONE!')
