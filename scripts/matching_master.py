import logging
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import re
import shapely
import sys
from pathlib import Path
from dotenv import load_dotenv
from bisect import bisect
from collections import OrderedDict
from operator import add, index, itemgetter
from shapely import geometry
from shapely.geometry import Point, Polygon, MultiPolygon
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

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
    "Step 4: Converts linkages to integer tuples, if possible"
    try:
        if isinstance(val, int):
            return val
        else:
            return int(val)
    except ValueError:
        return val

def get_unlinked_geometry(footprint_gdf, addresses_gdf , buffer_distances):
    'Returns indexes for the bf based on the increasing buffer size'
    
    def list_ap_indexes(buffer_geom, ap_gdf):
        """
        For parcel-less bf geometry takes the buffer from the buffer_geom field and looks for 
        intersects based on the buffer geom. Returns a list of all indexes with true values.
        """
        intersects = ap_gdf.intersects(buffer_geom)
        intersects = intersects[intersects == True]
        intersects = tuple(intersects.index)
        if len(intersects) > 0:
            return intersects
        else: 
            return np.nan
    
    
    footprint_gdf['method'] = np.nan
    linked_dfs = []
    
    for dist in buffer_distances:
        
        footprint_gdf['buffer_geom'] = footprint_gdf.geometry.buffer(dist)
        footprint_gdf[f'addresses_index'] = footprint_gdf['buffer_geom'].apply(lambda point_buffer: list_ap_indexes(point_buffer, addresses_gdf))

        linked_df = footprint_gdf.dropna(axis=0, subset=[f'addresses_index'])
        linked_df['method'] = f'{dist}m buffer'
        linked_df.drop(columns=["buffer_geom"], inplace=True)
        linked_dfs.append(linked_df)
        
        footprint_gdf = footprint_gdf[~footprint_gdf.index.isin(list(set(linked_df.index.tolist())))]
        footprint_gdf.drop(columns=["buffer_geom"], inplace=True)
        
        if len(addresses_gdf) == 0:
            break

    master_gdf = pd.concat(linked_dfs)
    return master_gdf

def get_nearest_linkage(poly, address_indexes):
    """Returns the footprint index associated with the nearest footprint geometry to the given address point."""  
    # Get footprint geometries.
    address_geometries = tuple(map(lambda index: addresses["geometry"].loc[addresses.index == index], address_indexes))
    # Get footprint distances from address point.
    address_distances = tuple(map(lambda address: address.distance(poly), address_geometries))                                     
    distance_values = [a[a.index == a.index[0]].values[0] for a in address_distances if len(a.index) != 0]
    distance_indexes = [a.index[0] for a in address_distances if len(a.index) != 0]
    
    if len(distance_indexes) == 0: # If empty then return drop val
        return np.nan
    
    address_index =  distance_indexes[distance_values.index(min(distance_values))]
    return address_index
    
def check_for_intersects(poly, address_indexes):
    '''Similar to the get nearest linkage function except this looks for intersects (uses within because its much faster) and spits out the index of any intersect'''
    address_geometries = tuple(map(lambda index: addresses["geometry"].loc[addresses.index == index], address_indexes))
    inter = tuple(map(lambda ap: poly.intersects(ap.iloc[0]), address_geometries))
    if True in inter:
        t_index = inter.index(True)
        return int(address_geometries[t_index].index[0])

# ---------------------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

output_path = os.getcwd()
output_gpkg = Path(os.getenv('MATCHED_OUTPUT_GPKG'))
# Layer inputs cleaned versions only
project_gpkg = Path(os.getenv('DATA_GPKG'))
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')
addresses_lyr_nme = os.getenv('CLEANED_AP_LYR_NAME')

proj_crs = int(os.getenv('PROJ_CRS'))

add_num_fld_nme =  os.getenv('AP_CIVIC_ADDRESS_FIELD_NAME')
unlinked_bf_lyr_nme = os.getenv('UNLINKED_BF_LYR_NME')

out_lyr_nme = os.getenv('LINKED_BY_DATA_NME')

buffer_distances = [5,10,20] # distance for the buffers

# ---------------------------------------------------------------------------------------------------------------
# Logic

print( "Running Step 1. Load dataframes and configure attributes")
# Load dataframes
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=26911)
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme, crs=26911)

addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)

# Define join fields.
join_footprint = 'link_field'
join_addresses = 'link_field'

print("Running Step 2. Configure address to footprint linkages")

# Link addresses and footprint on join fields.
addresses["addresses_index"] = addresses.index
footprint["footprint_index"] = footprint.index

merge = footprint.merge(addresses[[join_addresses, "addresses_index"]], how="left", left_on=join_footprint, right_on=join_addresses)
footprint['addresses_index'] = groupby_to_list(merge, "footprint_index", "addresses_index")

#addresses.drop(columns=["addresses_index"], inplace=True)
footprint.drop(columns=["footprint_index"], inplace=True)

# Extract non-linked addresses if any.
unlinked_bfs = footprint[footprint["addresses_index"].map(itemgetter(0)).isna()] # Seperate out for the buffer phase

# Discard non-linked addresses.
footprint.drop(footprint[footprint["addresses_index"].map(itemgetter(0)).isna()].index, axis=0, inplace=True)

# Get linkages via buffer if any unlinked data ia present
if len(unlinked_bfs) > 0:
    unlinked_bfs.drop(columns=['addresses_index'], inplace=True)
    unlinked_bfs.to_crs(proj_crs, inplace=True)
    unlinked_bfs = get_unlinked_geometry(unlinked_bfs, addresses, buffer_distances)
    footprint = footprint.append(unlinked_bfs)

print('Running Step 3. Checking address linkages via intersects')

footprint['intersect_index'] = footprint[["geometry", "addresses_index"]].apply(lambda row: check_for_intersects(*row), axis=1)
# Clean footprints remove none values and make sure that the indexes are integers
intersections = footprint.dropna(axis=0, subset=['intersect_index'])

footprint = footprint[footprint.intersect_index.isna()] # Keep only footprints that were not intersects
footprint.drop(columns=['intersect_index'], inplace=True) # Now drop the now useless intersects_index column

intersect_footprints = list(set(intersections.intersect_index.tolist()))

footprint.dropna(axis=0, subset=['addresses_index'], inplace=True)

intersections['intersect_index'] = intersections['intersect_index'].astype(int)

intersect_indexes = list(set(intersections.index.tolist()))

# intersections = addresses[addresses.index == intersect_indexes]
intersections['addresses_index'] = intersections['intersect_index']
intersections.drop(columns='intersect_index', inplace=True)
intersections['method'] = 'intersect'

addresses = addresses[~addresses.index.isin(list(set(intersections.addresses_index.tolist())))] # remove all addresses that were matched in the intersection stage

print('Running Step 4. Checking address linkages via closest adp limted by linking data')

# Ensure projected crs is used
intersections.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)
# intersections.to_crs(crs=proj_crs, inplace=True)

# Convert linkages to integer tuples, if possible.
footprint["addresses_index"] = footprint["addresses_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = footprint["addresses_index"].map(len) > 1
# Reduce plural linkages to the building segment with the lowest (nearest) geometric distance.

footprint.loc[flag_plural, "addresses_index"] = footprint[flag_plural][["geometry", "addresses_index"]].apply(
    lambda row: get_nearest_linkage(*row), axis=1) 

footprint = footprint[footprint['addresses_index'] != np.nan]
# Unpack first tuple element for singular linkages.
footprint.loc[~flag_plural, "addresses_index"] = footprint[~flag_plural]["addresses_index"].map(itemgetter(0))
footprint.method.fillna('data_linking', inplace=True)

print("Running Step 5. Merge Results to Polygons")

outgdf = footprint.append(intersections)
# outgdf = outgdf.merge(addresses, how='Left', left_on='addresses_index', right_index=True )
addresses.to_file(output_gpkg, layer='addresses_post_matching', driver='GPKG')
outgdf.to_file(output_gpkg, layer='footprint_linkages',  driver='GPKG')

print('DONE!')
