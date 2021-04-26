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
from operator import add, index, itemgetter
from shapely import geometry
from shapely.geometry import Point, Polygon, MultiPolygon
from dotenv import load_dotenv
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers

'''
This script is a proof of concept building on the work of Jessie Stewart for the NRN. This script attempts to take
building foorprints and match the best address point available to them in order to apply pertinent address fields
to the building fooprints.

'''
# ------------------------------------------------------------------------------------------------------------
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

def get_nearest_linkage(pt, footprint_indexes):
    """Returns the footprint index associated with the nearest footprint geometry to the given address point."""  
    # Get footprint geometries.
    footprint_geometries = tuple(map(lambda index: footprint["geometry"].loc[footprint.index == index], footprint_indexes))
    # Get footprint distances from address point.
    footprint_distances = tuple(map(lambda building: pt.distance(Point(building.centroid.x, building.centroid.y)), footprint_geometries))                                      
    # Get the footprint index associated with the smallest distance.
    footprint_index = footprint_indexes[footprint_distances.index(min(footprint_distances))]
    return footprint_index

def check_for_intersects_ap(address_gdf, footprint_gdf):
    ''' Check for cases of intersections between the building footprints layer and the address points layer output a spatial join of only the intersections between
    the two layers as a series. Building footprints are joined to the address points in this verison'''
    inter = address_gdf
    inter = gpd.sjoin(inter, footprint_gdf, how='left')
    inter = inter[inter['index_right'].notna()] # Drops all non matches from the match data frame
    #inter.to_file(r'H:\point_to_polygon_PoC\data\output.gpkg',  layer='intersect_test_ap_bf',  driver='GPKG')
    print( f'{len(inter)} intersects found between the address points and building footprints joining those matches together')
    inter['index_right'] = inter['index_right'].map(int)
    inter.rename({'index_right': 'footprint_index'}, axis='columns', inplace=True)
    return inter['footprint_index'] 
# ---------------------------------------------------------------------------------------------------------------
# Inputs

output_path = os.getcwd()
output_gpkg = r'H:\point_to_polygon_PoC\data\output.gpkg'
# Layer inputs cleaned versions only
project_gpkg = "H:/point_to_polygon_PoC/data/data.gpkg" 
footprints_lyr_nme = 'footprints_cleaned'
addresses_lyr_nme = 'addresses_cleaned'
# ---------------------------------------------------------------------------------------------------------------
# Logic

print( "Running Step 1. Load dataframes and configure attributes")
# Load dataframes
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=26911)
#footprint = gpd.read_file(footprints_path, layer='missing_intersects' , crs=26911) # spatial join between the parcels and building footprints layers
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme, crs=26911)
# Define join fields.
join_footprint = "STREET_NAME"
join_addresses = "STREET_NAME"

# Configure attributes - number and suffix.
addresses["suffix"] = addresses["CIVIC_ADDRESS"].map(lambda val: re.sub(pattern="\\d+", repl="", string=val, flags=re.I))
addresses["number"] = addresses["CIVIC_ADDRESS"].map(lambda val: re.sub(pattern="[^\\d]", repl="", string=val, flags=re.I)).map(int)

print('Running Step 2. Checking address linkages via intersects')

# Check for intersections
intersect_indexes = check_for_intersects_ap(addresses, footprint)
intersections = addresses.iloc[intersect_indexes.index.tolist()]
intersections['footprint_index'] = intersect_indexes
intersections['method'] = 'intersect'
intersected_bfs = footprint.iloc[list(set(intersect_indexes.tolist()))]
footprint.drop(intersect_indexes.tolist(), axis='rows', inplace=True) # Remove intersect footprints from the footprints gdf

intersections['footprint_geometry'] = intersections.merge(
intersected_bfs["geometry"], how="left", left_on="footprint_index", right_index=True)['geometry_y']
intersections.set_geometry('footprint_geometry')
intersections.drop(columns='geometry', inplace=True)
intersections.rename(columns={'footprint_geometry':'geometry'}, inplace=True)
intersections.to_file(output_gpkg, layer='intersects', driver='GPKG')

print("Running Step 3. Configure address to footprint linkages")

# Link addresses and footprint on join fields.
addresses["addresses_index"] = addresses.index
footprint["footprint_index"] = footprint.index

merge = addresses.merge(footprint[[join_footprint, "footprint_index"]], how="left", left_on=join_addresses, right_on=join_footprint)
addresses["footprint_index"] = groupby_to_list(merge, "addresses_index", "footprint_index")

addresses.drop(columns=["addresses_index"], inplace=True)
footprint.drop(columns=["footprint_index"], inplace=True)

# Discard non-linked addresses.
addresses.drop(addresses[addresses["footprint_index"].map(itemgetter(0)).isna()].index, axis=0, inplace=True)

# Convert linkages to integer tuples, if possible.

addresses["footprint_index"] = addresses["footprint_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = addresses["footprint_index"].map(len) > 1
# Reduce plural linkages to the building segment with the lowest (nearest) geometric distance.
addresses.loc[flag_plural, "footprint_index"] = addresses[flag_plural][["geometry", "footprint_index"]].apply(
    lambda row: get_nearest_linkage(*row), axis=1)

# Unpack first tuple element for singular linkages.
addresses.loc[~flag_plural, "footprint_index"] = addresses[~flag_plural]["footprint_index"].map(itemgetter(0))
addresses['method'] = 'data_linking'
# Merge the intersects data back with the linking data 

addresses = addresses.append(intersections, ignore_index= True)
#footprint = footprint.append(intersected_bfs)

# Compile linked footprint geometry for each address.
addresses["footprint_geometry"] = addresses.merge(
    footprint["geometry"], how="left", left_on="footprint_index", right_index=True)["geometry_y"]

print("Running Step 4. Merge Results to Polygons")

addresses.drop(columns='geometry', inplace=True)
addresses.rename(columns={'footprint_geometry':'geometry'}, inplace=True)
addresses.set_geometry('geometry')
addresses.to_file(output_gpkg, layer='addresses_poly_linked', driver='GPKG')

outgdf = addresses.append(intersections)
print(outgdf.head())
outgdf.to_file(output_gpkg, layer='inter_linked_merged',  driver='GPKG')
print('DONE!')
