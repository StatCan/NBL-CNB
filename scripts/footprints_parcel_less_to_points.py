import geopandas as gpd
import logging
import numpy as np
import os
import pandas as pd
import re 
import sys
from operator import add, index, itemgetter
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


# ---------------------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.path.dirname(__file__), 'environments.env'))

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

unlinked_lyr_nme = os.getenv('NT_UNLINKED_NME')
buffer_linked_lyr_nme = os.getenv('NT_LINKED_BY_BUFFER_NME')

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

footprint = get_unlinked_geometry(footprint, addresses, buffer_dists)

addresses.drop(columns=["addresses_index"], inplace=True)

# Convert linkages to integer tuples, if possible.

footprint["addresses_index"] = footprint["addresses_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = footprint["addresses_index"].map(len) > 1
# Reduce plural linkages to the building segment with the lowest (nearest) geometric distance.
footprint.loc[flag_plural, "addresses_index"] = footprint[flag_plural][["geometry", "addresses_index"]].apply(
    lambda row: get_nearest_linkage(*row), axis=1)

# Unpack first tuple element for singular linkages.
footprint.loc[~flag_plural, "addresses_index"] = footprint[~flag_plural]["addresses_index"].map(itemgetter(0))

reject_gdf = footprint[footprint.addresses_index.isna()]
if len(reject_gdf) > 0:
    reject_gdf.to_file(output_gpkg, layer=unlinked_lyr_nme,  driver='GPKG') # export the rejects as a layer
del reject_gdf

print("Running Step 3. Merge Results to Polygons")

out_gdf = gpd.GeoDataFrame(footprint, geometry='geometry', crs=26911)
print(out_gdf.head())
sys.exit()
out_gdf.drop(columns='geometry', inplace=True)
out_gdf.to_file(output_gpkg, layer=buffer_linked_lyr_nme, driver='GPKG')
print('DONE!')