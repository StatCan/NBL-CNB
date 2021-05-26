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
from pathlib import Path
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

'''

Experimental version of the script testing ground for the cases with no linking methodology

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
    addresses['method'] = np.nan
    linked_dfs = []
    for dist in buffer_distances:
        addresses_gdf['buffer_geom'] = addresses_gdf.geometry.buffer(dist)
        addresses_gdf[f'footprint_index'] = addresses_gdf['buffer_geom'].apply(lambda point_buffer: list_bf_indexes(point_buffer, footprint_gdf))
        linked_df = addresses_gdf.dropna(axis=0, subset=[f'footprint_index'])
        linked_df['method'] = f'{dist}m buffer'
        linked_df.drop(columns=["buffer_geom"], inplace=True)
        linked_dfs.append(linked_df)
        addresses_gdf = addresses_gdf[~addresses_gdf.index.isin(list(set(linked_df.index.tolist())))]
        addresses_gdf.drop(columns=["buffer_geom"], inplace=True)
    master_gdf = pd.concat(linked_dfs)
    
    addresses_gdf.to_file(output_gpkg, layer='non_geolinked',  driver='GPKG') # export the rejects as a layer
    return master_gdf

def get_nearest_linkage(pt, footprint_indexes):
    """Returns the footprint index associated with the nearest footprint geometry to the given address point."""  
    # Get footprint geometries.
    footprint_geometries = tuple(map(lambda index: footprint["geometry"].loc[footprint.index == index], footprint_indexes))
    # Get footprint distances from address point.
    footprint_distances = tuple(map(lambda building: building.boundary.distance(pt), footprint_geometries))                                     
    distance_values = [f[f.index == f.index[0]].values[0] for f in footprint_distances if len(f.index) != 0]
    distance_indexes = [f.index[0] for f in footprint_distances if len(f.index) != 0]
    if len(distance_indexes) == 0: # If empty then return drop val
        return np.nan
    footprint_index =  distance_indexes[distance_values.index(min(distance_values))]
    return footprint_index
  
# ---------------------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.getcwd(), 'environments.env'))

output_path = os.getcwd()
output_gpkg = Path(os.getenv('NT_FINAL_OUTPUT'))
buffer_dists = [5, 10, 20] # Max distance of buffer the non linking data will have in Metres 

# Layer inputs
project_gpkg = os.getenv('NT_GPKG')
footprints_lyr_nme = os.getenv('UNLINKED_BF_LYR_NME')
addresses_lyr_nme = os.getenv('CLEANED_AP_LYR_NAME')

# Other inputs
proj_crs = int(os.getenv('NT_PROJ_CRS'))
geo_crs = int(os.getenv('NT_CRS'))

# ---------------------------------------------------------------------------------------------------------------
# Logic

print( "Running Step 1. Load dataframes and configure attributes")

# Load dataframes.
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme)
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme)

addresses.to_crs(proj_crs, inplace=True)
footprint.to_crs(proj_crs, inplace=True)

print("Running Step 2. Configure address to footprint linkages")
# Link addresses and footprint on join fields.
addresses["addresses_index"] = addresses.index
footprint["footprint_index"] = footprint.index

addresses = get_unlinked_geometry(addresses, footprint, buffer_dists)

footprint.drop(columns=["footprint_index"], inplace=True)

# Convert linkages to integer tuples, if possible.

addresses["footprint_index"] = addresses["footprint_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = addresses["footprint_index"].map(len) > 1
# Reduce plural linkages to the building segment with the lowest (nearest) geometric distance.
addresses.loc[flag_plural, "footprint_index"] = addresses[flag_plural][["geometry", "footprint_index"]].apply(
    lambda row: get_nearest_linkage(*row), axis=1)

# Unpack first tuple element for singular linkages.
addresses.loc[~flag_plural, "footprint_index"] = addresses[~flag_plural]["footprint_index"].map(itemgetter(0))

# Compile linked footprint geometry for each address.
addresses["footprint_geometry"] = addresses.merge(
    footprint["geometry"], how="left", left_on="footprint_index", right_index=True)["geometry_y"]

print("Running Step 3. Merge Results to Polygons")
# Import the building polygons
#building_polys = gpd.read_file(project_gpkg, layer= bf_polys)
#out_gdf = building_polys.merge(addresses[['footprint_index', 'number', 'suffix', 'CIVIC_ADDRESS', 'STREET_NAME']], how="left", right_on="footprint_index", left_index=True)
#out_gdf.to_file(os.path.join(output_path, 'test_to_polygon edge.shp'))
out_gdf = gpd.GeoDataFrame(addresses, geometry='footprint_geometry', crs=26911)
out_gdf.drop(columns='geometry', inplace=True)
print(out_gdf.head())
out_gdf.to_file(project_gpkg, layer='', driver='GPKG')
print('DONE!')