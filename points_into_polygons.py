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
    # Step 2: Converts linkages to integer tuples, if possible
    try:
        return int(val)
    except ValueError:
        return val

# ---------------------------------------------------------------------------------------------------------------
# Inputs

# Define index of example roadseg segment.
ex_idx = 264
ex_place = "City of Yellowknife"



# ---------------------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
addresses = gpd.read_file("H:/point_to_polygon_PoC/data/data.gpkg", layer="yk_Address_Points")
roadseg = gpd.read_file("H:/point_to_polygon_PoC/data/data.gpkg", layer="yk_buildings_sj") # spatial joine between the parcels and building footprints layers

# Clean data
# Remove rite of way from the address data and join count > 0
addresses = addresses[(addresses.CIVIC_ADDRESS != "RITE OF WAY")]
# Remove null street name rows
roadseg = roadseg[(roadseg.Join_Count > 0) & (roadseg.STREET_NAME.notnull())] 

#Step 1. Load dataframes and configure attributes
# Define join fields.
join_roadseg = "STREET_NAME"
join_addresses = "STREET_NAME"

# Configure attributes - number and suffix.
addresses["suffix"] = addresses["CIVIC_ADDRESS"].map(lambda val: re.sub(pattern="\\d+", repl="", string=val, flags=re.I))
addresses["number"] = addresses["CIVIC_ADDRESS"].map(lambda val: re.sub(pattern="[^\\d]", repl="", string=val, flags=re.I)).map(int)

# Step 2. Configure address to roadseg linkages
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

print(addresses.head())

print('DONE!')
