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

pd.options.mode.chained_assignment = None

'''

Test script to determine feasability of separating out mobile home parks or other neighborhoods types contained in one large parcel with many point and many buildings

Single match per address point in these cases as opposed to the other many to many situations as it is safe to assume that each building in the development 

'''

# ---------------------------------------------------------------------------------------------------------------
# Functions

def get_unlinked_geometry(addresses_gdf, footprint_gdf , buffer_distances):
    'Returns indexes for the bf based on a buffer'
    
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

def get_nearest_linkage(ap, footprint_indexes):
    """Returns the footprint index associated with the nearest footprint geometry to the given address point."""  
    # Get footprint geometries.
    footprint_geometries = tuple(map(lambda index: footprint["geometry"].loc[footprint.index == index], footprint_indexes))
    # Get footprint distances from address point.
    footprint_distances = tuple(map(lambda footprint: footprint.distance(ap), footprint_geometries))                                     
    distance_values = [a[a.index == a.index[0]].values[0] for a in footprint_distances if len(a.index) != 0]
    distance_indexes = [a.index[0] for a in footprint_distances if len(a.index) != 0]

    if len(distance_indexes) == 0: # If empty then return drop val
        return np.nan

    footprint_index =  distance_indexes[distance_values.index(min(distance_values))]
    return footprint_index

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
addresses_lyr_nme = os.getenv('FLAGGED_AP_LYR_NME')

proj_crs = int(os.getenv('PROJ_CRS'))

add_num_fld_nme =  os.getenv('AP_CIVIC_ADDRESS_FIELD_NAME')
unlinked_bf_lyr_nme = os.getenv('UNLINKED_BF_LYR_NME')

out_lyr_nme = os.getenv('LINKED_BY_DATA_NME')

buffer_distances = [5,10,20] # distance for the buffers

bp_threshold = 20 # Min number of address points in a parcel needed before the bp method is triggered

# ---------------------------------------------------------------------------------------------------------------
# Logic

addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs)
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme, crs=proj_crs)

addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)

# Define join fields.
join_footprint = 'link_field'
join_addresses = 'link_field'

# Link addresses and footprint on join fields.
addresses["addresses_index"] = addresses.index
footprint["footprint_index"] = footprint.index

# CODE TO BE COPIED INTO MATCHING MASTER HERE

ap_counts = addresses.groupby('link_field', dropna=True)['link_field'].count()

# Take only parcels that have more than the big parcel (bp) threshold intersects of both a the inputs
addresses_bp = addresses.loc[addresses['link_field'].isin(ap_counts[ap_counts > bp_threshold].index.tolist())]

addresses_bp = get_unlinked_geometry(addresses_bp, footprint, buffer_distances)
ap_bp_plural = addresses_bp['footprint_index'].map(len) > 1

addresses_bp.loc[ap_bp_plural, "footprint_index"] = addresses_bp[ap_bp_plural][["geometry", "footprint_index"]].apply(lambda row: get_nearest_linkage(*row), axis=1) 

addresses_bp.loc[~ap_bp_plural, "footprint_index"] = addresses_bp[~ap_bp_plural]["footprint_index"].map(itemgetter(0))

# STOP COPYING HERE AS STEP 6 IS ALREADY IN MATCHING MASTER

print("Running Step 6: Change Point Location to Building Centroid")
print('     Creating footprint centroids')
footprint['centroid_geo'] = footprint['geometry'].apply(lambda bf: bf.centroid)
print('     Matching address points with footprint centroids')
addresses_bp['out_geom'] = addresses_bp['footprint_index'].apply(lambda row: create_centroid_match(row, footprint['centroid_geo']))

addresses_bp = addresses_bp.set_geometry('out_geom')

addresses_bp.drop(columns='geometry', inplace=True)
addresses_bp.rename(columns={'out_geom':'geometry'}, inplace=True)
addresses_bp = addresses_bp.set_geometry('geometry')

addresses_bp.to_file(output_gpkg, layer='addresses_bp_test',  driver='GPKG')


# print(addresses_bp.head())
# print(footprint_bp[footprint_bp['footprint_index'].isin([14846, 16387, 16272, 8958, 14931])].head())

print('DONE!')
