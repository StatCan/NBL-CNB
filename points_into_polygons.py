import geopandas as gpd
import logging
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
from dotenv import load_dotenv
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers

pd.options.mode.chained_assignment = None # Gets rod pf annoying warning

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
    footprint_distances = tuple(map(lambda building: building.boundary.distance(pt), footprint_geometries))                                     
    # Get the footprint index associated with the smallest distance.
    distances = pd.Series([f.iloc[0] for f in footprint_distances], index= [footprint.index[0] for footprint in footprint_distances]) # Cleaning because outputs are messy
    minimum_index = distances.index[distances == distances.min()][0]
    
    if minimum_index in footprint_indexes:
        return minimum_index
    else:
        print(f'{minimum_index}: not in footprint_indexes. Error try again.')
        sys.exit()

def check_for_intersects(pt, footprint_indexes):
    '''Similar to the get nearest linkage function except this looks for intersects (uses within because its much faster) and spits out the index of any intersect'''
    footprint_geometries = tuple(map(lambda index: footprint["geometry"].loc[footprint.index == index], footprint_indexes))
    inter = tuple(map(lambda building: pt.within(building.iloc[0]), footprint_geometries))
    if True in inter:
        t_index = inter.index(True)
        return footprint_geometries[t_index].index[0]

def check_for_intersects_ap(address_gdf, footprint_gdf):
    ''' Check for cases of intersections between the building footprints layer and the address points layer output a spatial join of only the intersections between
    the two layers as a series. Building footprints are joined to the address points in this verison'''
    
    def get_intersect_linkage(pt, footprints):
        print(pt[0].x)
        pt = Point(pt[0].x, pt[0].y)
        geometries = tuple(map(lambda building: pt.within(building), footprints))
        print(geometries)
        sys.exit()

    inter = address_gdf
    print(footprint_gdf.geometry)
    inter['flag_intersect'] =  inter[["geometry"]].apply(lambda row: get_intersect_linkage(row, footprint_gdf.geometry), axis=1) #  <--- Fix this whole row and function
    sys.exit()
    inter = gpd.sjoin(inter, footprint_gdf, how='left', op='within')
    inter = inter[inter['index_right'].notna()] # Drops all non matches from the match data frame
    print( f'   {len(inter)} intersects found between the address points and building footprints joining those matches together')
    inter['index_right'] = inter['index_right'].map(int)
    inter.rename({'index_right': 'footprint_index'}, axis='columns', inplace=True)
    return inter['footprint_index'] 

def cut_indexes(bf_ind_list, cut_ind_lst):
    ''' Way to remove the index from the footprint index column so that things aren't looked at that have already been matched'''

    if isinstance(bf_ind_list, list):
        reduced_list = [i for i in bf_ind_list if i not in cut_ind_lst]
        if len(reduced_list) == 1:
            return reduced_list[0]
        if len(reduced_list) == 0:
            return -99
        if len(reduced_list) > 0:
            return reduced_list

    if isinstance(bf_ind_list, int):
        if bf_ind_list in cut_ind_lst:
            return -99
        if bf_ind_list not in cut_ind_lst:
            return bf_ind_list
    else: 
        print(f'Unaccounted for list of type {type(bf_ind_list)} in index cutting function. Account for this.')
        sys.exit()
# ---------------------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.getcwd(), 'environments.env'))

output_path = os.getcwd()
output_gpkg = Path(os.getenv('NT_FINAL_OUTPUT'))
# Layer inputs cleaned versions only
project_gpkg = os.getenv('NT_GPKG')
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')
addresses_lyr_nme = os.getenv('CLEANED_AP_LYR_NAME')

proj_crs = int(os.getenv('NT_PROJ_CRS'))

add_num_fld_nme =  os.getenv('AP_CIVIC_ADDRESS_FIELD_NAME')
# ---------------------------------------------------------------------------------------------------------------
# Logic

print( "Running Step 1. Load dataframes and configure attributes")
# Load dataframes
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=26911)
#footprint = gpd.read_file(footprints_path, layer='missing_intersects' , crs=26911) # spatial join between the parcels and building footprints layers
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme, crs=26911)
# Define join fields.
join_footprint = 'link_field'
join_addresses = 'link_field'

# Configure attributes - number and suffix.
# addresses["suffix"] = addresses[add_num_fld_nme].map(lambda val: re.sub(pattern="\\d+", repl="", string=val, flags=re.I))
# addresses["number"] = addresses[add_num_fld_nme].map(lambda val: re.sub(pattern="[^\\d]", repl="", string=val, flags=re.I)).map(int)

# Check for intersections
# intersect_indexes = check_for_intersects_ap(addresses, footprint)
# intersections = addresses.iloc[intersect_indexes.index.tolist()]
# intersections['footprint_index'] = intersect_indexes
# intersections['method'] = 'intersect'
# intersected_bfs = footprint.iloc[list(set(intersect_indexes.tolist()))]
# footprint.drop(intersect_indexes.tolist(), axis='rows', inplace=True) # Remove intersect footprints from the footprints gdf

# intersections['footprint_geometry'] = intersections.merge(
# intersected_bfs["geometry"], how="left", left_on="footprint_index", right_index=True)['geometry_y']
# intersections.set_geometry('footprint_geometry')
# intersections.drop(columns='geometry', inplace=True)
# intersections.rename(columns={'footprint_geometry':'geometry'}, inplace=True)

print("Running Step 2. Configure address to footprint linkages")

# Link addresses and footprint on join fields.
addresses["addresses_index"] = addresses.index
footprint["footprint_index"] = footprint.index

merge = addresses.merge(footprint[[join_footprint, "footprint_index"]], how="left", left_on=join_addresses, right_on=join_footprint)
addresses["footprint_index"] = groupby_to_list(merge, "addresses_index", "footprint_index")

addresses.drop(columns=["addresses_index"], inplace=True)
footprint.drop(columns=["footprint_index"], inplace=True)

# Discard non-linked addresses.
addresses.drop(addresses[addresses["footprint_index"].map(itemgetter(0)).isna()].index, axis=0, inplace=True)

print('Running Step 3. Checking address linkages via intersects')
# Check for intersections
intersects = addresses[["geometry", "footprint_index"]].apply(lambda row: check_for_intersects(*row), axis=1)
footprint.drop(intersects.loc[~np.isnan(intersects)].tolist(), axis='rows', inplace=True) # Drop linked footprints from the footprints dataset

intersects = intersects.loc[~np.isnan(intersects)]
intersect_indexes = intersects.loc[~np.isnan(intersects)].index.tolist()
intersections = addresses[addresses.index == intersect_indexes]
intersections['footprint_index'] = intersect_indexes
intersections['method'] = 'intersect'
intersected_bfs = footprint[footprint.index == list(set(intersect_indexes))]

intersections['footprint_geometry'] = intersections.merge(
intersected_bfs["geometry"], how="left", left_on="footprint_index", right_index=True)['geometry_y']
intersections.set_geometry('footprint_geometry')
intersections.drop(columns='geometry', inplace=True)
intersections.rename(columns={'footprint_geometry':'geometry'}, inplace=True)

addresses['footprint_index'] = addresses['footprint_index'].apply(lambda row: cut_indexes(row, intersect_indexes))  # Remove index from index lists that have been already been matched via intersect
addresses = addresses.loc[addresses.footprint_index != -99]
print('Running Step 4. Checking address linkages via closest adp limted by linking data')

# Ensure projected crs is used
addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)

# Convert linkages to integer tuples, if possible.
addresses["footprint _index"] = addresses["footprint_index"].map(lambda vals: tuple(set(map(as_int, vals))))

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

print("Running Step 5. Merge Results to Polygons")

addresses.drop(columns='geometry', inplace=True)
addresses.rename(columns={'footprint_geometry':'geometry'}, inplace=True)
addresses.set_geometry('geometry')
addresses.to_file(output_gpkg, layer='addresses_poly_linked', driver='GPKG')

outgdf = addresses.append(intersections)

outgdf.to_file(output_gpkg, layer='inter_linked_merged',  driver='GPKG')
print('DONE!')
