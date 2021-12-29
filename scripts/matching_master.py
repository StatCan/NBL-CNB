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
import datetime

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

'''

This script is a proof of concept building on the work of Jessie Stewart for the NRN. This script attempts to take
building footprints and match them to an address point. Multiple copies of an address points created if there are 
multiple buildings but only 1 address point. This script will return a point layer with each record containing a
link to a building footprint

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

def get_unlinked_geometry(addresses_gdf, footprint_gdf , buffer_distances):
    'Returns indexes for the bf based on the increasing buffer size'
    
    def list_bf_indexes(buffer_geom, bf_gdf):
        """
        For parcel-less bf geometry takes the buffer from the buffer_geom field and looks for 
        intersects based on the buffer geom. Returns a list of all indexes with true values.
        """
        intersects = bf_gdf.intersects(buffer_geom)
        intersects = intersects[intersects == True]
        intersects = tuple(intersects.index)
        if len(intersects) > 0:
            return intersects
        else: 
            return np.nan
    
    
    addresses_gdf['method'] = np.nan
    linked_dfs = []
    
    for dist in buffer_distances:
        
        addresses_gdf['buffer_geom'] = addresses_gdf.geometry.buffer(dist)
        addresses_gdf[f'footprint_index'] = addresses_gdf['buffer_geom'].apply(lambda point_buffer: list_bf_indexes(point_buffer, footprint_gdf))

        linked_df = addresses_gdf.dropna(axis=0, subset=[f'footprint_index'])
        linked_df['method'] = f'{dist}m buffer'
        linked_df.drop(columns=["buffer_geom"], inplace=True)
        linked_dfs.append(linked_df)
        
        addresses_gdf = addresses_gdf[~addresses_gdf.index.isin(list(set(linked_df.index.tolist())))]
        
        # addresses.drop(columns=["buffer_geom"], inplace=True)
        
        if len(addresses_gdf) == 0:
            break

    master_gdf = pd.concat(linked_dfs)
    return master_gdf

def check_for_intersects(address_pt, footprint_indexes):
    '''Similar to the get nearest linkage function except this looks for intersects (uses within because its much faster) and spits out the index of any intersect'''
    footprint_geometries = tuple(map(lambda index: footprint["geometry"].loc[footprint.index == index], footprint_indexes))
    inter = tuple(map(lambda bf: address_pt.within(bf.iloc[0]), footprint_geometries))
    if True in inter:
        t_index = inter.index(True)
        return int(footprint_geometries[t_index].index[0])

def create_centroid_match(footprint_index, bf_centroids):
    '''Returns the centroid geometry for a given point'''
    new_geom = bf_centroids.iloc[int(footprint_index)]
    return new_geom

# ---------------------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

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

print('     creating and grouping linkages')
merge = addresses.merge(footprint[[join_footprint, "footprint_index"]], how="left", left_on=join_addresses, right_on=join_footprint)
addresses['footprint_index'] = groupby_to_list(merge, "addresses_index", "footprint_index")

addresses.drop(columns=["addresses_index"], inplace=True)

# Extract non-linked addresses if any.
print('     extracting unlinked addresses')
unlinked_aps = addresses[addresses["footprint_index"].map(itemgetter(0)).isna()] # Seperate out for the buffer phase
# Discard non-linked addresses.
addresses.drop(addresses[addresses["footprint_index"].map(itemgetter(0)).isna()].index, axis=0, inplace=True)

# Get linkages via buffer if any unlinked data ia present
print('     get linkages via buffer')
if len(unlinked_aps) > 0:
    unlinked_aps.drop(columns=['footprint_index'], inplace=True)
    unlinked_aps.to_crs(proj_crs, inplace=True)
    print('     processing unlinked geometry')
    # run the next line using only the footprints that are not already linked to an address point
    unlinked_aps = get_unlinked_geometry(unlinked_aps, footprint[~footprint['footprint_index'].isin(addresses.footprint_index.explode().unique().tolist())], buffer_distances)
    print('     appending unlinked geometry to address data')
    addresses = addresses.append(unlinked_aps)
    
print('Running Step 3. Checking address linkages via intersects')

addresses['intersect_index'] = addresses[["geometry", "footprint_index"]].apply(lambda row: check_for_intersects(*row), axis=1)
# Clean footprints remove none values and make sure that the indexes are integers
intersections = addresses.dropna(axis=0, subset=['intersect_index'])

addresses = addresses[addresses.intersect_index.isna()] # Keep only address points that were not intersects
addresses.drop(columns=['intersect_index'], inplace=True) # Now drop the now useless intersects_index column

intersect_a_points = list(set(intersections.intersect_index.tolist()))

addresses.dropna(axis=0, subset=['footprint_index'], inplace=True)

intersections['intersect_index'] = intersections['intersect_index'].astype(int)

intersect_indexes = list(set(intersections.index.tolist()))

intersections['footprint_index'] = intersections['intersect_index']
intersections.drop(columns='intersect_index', inplace=True)
intersections['method'] = 'intersect'

# footprint = footprint[~footprint.index.isin(list(set(intersections.footprint_index.tolist())))] # remove all footprints that were matched in the intersection stage

print('Running Step 4. Checking address linkages via closest adp limited by linking data')

# Ensure projected crs is used
intersections.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)
# intersections.to_crs(crs=proj_crs, inplace=True)

# Convert linkages to integer tuples, if possible.
addresses["footprint_index"] = addresses["footprint_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = addresses["footprint_index"].map(len) > 1
addresses = addresses.explode('footprint_index') # Convert the lists into unique rows per building linkage (cleaned up later)

addresses = addresses[addresses['footprint_index'] != np.nan]
addresses.method.fillna('data_linking', inplace=True)

print("Running Step 5. Merge Results")

outgdf = addresses.append(intersections)

print("Running Step 6: Change Point Location to Building Centroid")
print('     Creating footprint centroids')
footprint['centroid_geo'] = footprint['geometry'].apply(lambda bf: bf.centroid)
print('     Matching address points with footprint centroids')
outgdf['out_geom'] = outgdf['footprint_index'].apply(lambda row: create_centroid_match(row, footprint['centroid_geo']))

outgdf = outgdf.set_geometry('out_geometry')
outgdf.drop('geometry', inplace=True)
outgdf.rename(columns={'out_geometry':'geometry'}, inplace=True)
outgdf = outgdf.set_geometry('geometry')

outgdf.to_file(output_gpkg, layer='point_linkages',  driver='GPKG')

end_time = datetime.datetime.now()

print(f'Start Time: {start_time}')
print(f'End Time: {end_time}')
print(f'Total Runtime: {end_time - start_time}')

print('DONE!')
