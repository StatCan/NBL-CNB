import geopandas as gpd
import numpy as np
import shapely
import os
import pandas as pd
import sys
from pathlib import Path
from dotenv import load_dotenv
from operator import itemgetter
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import datetime

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

'''

This script attempts to take building footprints and match them to an address point. Multiple copies of an address 
points created if there are multiple buildings but only 1 address point. In cases where there are many buildings
and many address points a copy of each address point will be placed on each building unless otherwise stated. 

This script will return a point layer with each record containing a link to a building footprint. 

Unlinked addresses and buildings will then be output for further analysis.

'''
# ------------------------------------------------------------------------------------------------------------
# Functions

def groupby_to_list(df, group_field, list_field) -> pd.Series:
    
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


def as_int(val) -> int:
    "Step 4: Converts linkages to integer tuples, if possible"
    try:
        if isinstance(val, int):
            return val
        else:
            return int(val)
    except ValueError:
        return val


def get_unlinked_geometry(addresses_gdf: gpd.GeoDataFrame, footprint_gdf: gpd.GeoDataFrame , buffer_distance:int) ->gpd.GeoDataFrame:
    'Returns indexes for the bf based on the buffer size'
    
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
    
    addresses_gdf['buffer_geom'] = addresses_gdf.geometry.buffer(buffer_distance)
    addresses_gdf[f'footprint_index'] = addresses_gdf['buffer_geom'].apply(lambda point_buffer: list_bf_indexes(point_buffer, footprint_gdf))

    linked_df = addresses_gdf.dropna(axis=0, subset=[f'footprint_index'])
    linked_df['method'] = f'{buffer_distance}m buffer'
    linked_df.drop(columns=["buffer_geom"], inplace=True)
    addresses_gdf = addresses_gdf[~addresses_gdf.index.isin(list(set(linked_df.index.tolist())))]
    return linked_df


def check_for_intersects(address_pt: shapely.geometry.Point, footprint_indexes) -> int:
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


def building_area_theshold_id(building_gdf, bf_area_threshold , area_field_name='bf_area'):
    '''
    Returns a boolean on whether a majority of the buildings in the bp fall under the bp threshold defined in the environments. 
    Buildings should be filtered to only those in the polygon before being passed into this function
    '''
    
    all_bf_cnt = len(building_gdf)

    bf_u_thresh = building_gdf[building_gdf[area_field_name] <= bf_area_threshold]
    bf_u_thresh_cnt = len(bf_u_thresh)

    if bf_u_thresh_cnt >= (all_bf_cnt/2):
        return True
    else:
        return False


# ---------------------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()
print(f'Start Time {start_time}')

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

output_path = os.getcwd()
output_gpkg = Path(os.getenv('MATCHED_OUTPUT_GPKG'))
matched_lyr_nme = os.getenv('MATCHED_OUTPUT_LYR_NME')
unmatched_lyr_nme = os.getenv('UNMATCHED_OUTPUT_LYR_NME')
unmatched_poly_lyr_nme = os.getenv('UNMATCHED_POLY_LYR_NME')

# Layer inputs cleaned versions only
project_gpkg = Path(os.getenv('DATA_GPKG'))
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')
addresses_lyr_nme = os.getenv('FLAGGED_AP_LYR_NME')

proj_crs = int(os.getenv('PROJ_CRS'))

add_num_fld_nme =  os.getenv('AP_CIVIC_ADDRESS_FIELD_NAME')
unlinked_bf_lyr_nme = os.getenv('UNLINKED_BF_LYR_NME')

out_lyr_nme = os.getenv('LINKED_BY_DATA_NME')

buffer_size = 20 # distance for the buffer

metrics_out_path = Path(os.getenv('METRICS_CSV_OUT_PATH'))

bp_threshold = int(os.getenv('BP_THRESHOLD'))
bp_area_threshold = int(os.getenv('BP_AREA_THRESHOLD'))

# ---------------------------------------------------------------------------------------------------------------
# Logic

print( "Running Step 1. Load dataframes and configure attributes")
# Load dataframes
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs)
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme, crs=proj_crs)

addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)

# Define join fields.
join_footprint = 'link_field'
join_addresses = 'link_field'

print("Running Step 2. Configure address to footprint linkages")

# Link addresses and footprint on join fields.

addresses["addresses_index"] = addresses.index
footprint["footprint_index"] = footprint.index

# Remove buildings flagged as sheds as they do not need to be matched
sheds = footprint[footprint['shed_flag'] == True] # Set aside for use in future if sheds need to be matched
footprint = footprint[footprint['shed_flag'] == False]

print('     creating and grouping linkages')
merge = addresses[~addresses[join_addresses].isna()].merge(footprint[[join_footprint, "footprint_index"]], how="left", left_on=join_addresses, right_on=join_footprint)
addresses['footprint_index'] = groupby_to_list(merge, "addresses_index", "footprint_index")
addresses.drop(columns=["addresses_index"], inplace=True)

# Big Parcel (BP) case extraction (remove and match before all other cases)
bf_counts = footprint.groupby('link_field', dropna=True)['link_field'].count()
ap_counts = addresses.groupby('link_field', dropna=True)['link_field'].count()

# Take only parcels that have more than the big parcel (bp) threshold intersects of both a the inputs
addresses_bp = addresses.loc[(addresses['link_field'].isin(bf_counts[bf_counts > bp_threshold].index.tolist())) & (addresses['link_field'].isin(ap_counts[ap_counts > bp_threshold].index.tolist()))]

if len(addresses_bp) > 0:
    # return all addresses with a majority of the buildings under the area threshold
    addresses_bp['u_areaflag'] = addresses_bp['footprint_index'].apply(lambda x: building_area_theshold_id(footprint[footprint['footprint_index'].isin(x)], bp_area_threshold)) 
    addresses_bp = addresses_bp.loc[addresses_bp['u_areaflag'] == True]
    addresses_bp.drop(columns=['u_areaflag'], inplace=True)

    addresses =  addresses[~addresses.index.isin(addresses_bp.index.tolist())]
    addresses_bp = get_unlinked_geometry(addresses_bp, footprint, buffer_distance=buffer_size)

    # Find and reduce plural linkages to the closest linkage
    ap_bp_plural = addresses_bp['footprint_index'].map(len) > 1
    addresses_bp.loc[ap_bp_plural, "footprint_index"] = addresses_bp[ap_bp_plural][["geometry", "footprint_index"]].apply(lambda row: get_nearest_linkage(*row), axis=1)
    addresses_bp.loc[~ap_bp_plural, "footprint_index"] = addresses_bp[~ap_bp_plural]["footprint_index"].map(itemgetter(0))
    addresses_bp['method'] = addresses_bp['method'].astype(str) + '_bp'
    addresses_bp['method'] = addresses_bp['method'].str.replace(' ','_')

# Extract non-linked addresses if any.
print('     extracting unlinked addresses')
addresses_na = addresses[addresses['footprint_index'].isna()] # Special cases with NaN instead of a tuple
addresses = addresses[~addresses.index.isin(addresses_na.index.tolist())]

unlinked_aps = addresses[addresses["footprint_index"].map(itemgetter(0)).isna()] # Extract unlinked addresses
if len(addresses_na) > 0:    
    unlinked_aps = unlinked_aps.append(addresses_na) # append unlinked addresses to the addresses_na

# Separate out for the buffer phase
# Discard non-linked addresses.
addresses.drop(addresses[addresses["footprint_index"].map(itemgetter(0)).isna()].index, axis=0, inplace=True)

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
print('Running Step 4. Creating address linkages using linking data')

# Ensure projected crs is used
intersections.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)

# Convert linkages to integer tuples, if possible.
addresses["footprint_index"] = addresses["footprint_index"].map(lambda vals: tuple(set(map(as_int, vals))))

# Flag plural linkages.
flag_plural = addresses["footprint_index"].map(len) > 1
addresses = addresses.explode('footprint_index') # Convert the lists into unique rows per building linkage (cleaned up later)

addresses = addresses[addresses['footprint_index'] != np.nan]
addresses['method'] = 'data_linking'

# Get linkages via buffer if any unlinked data is present
print('     get linkages via buffer')
if len(unlinked_aps) > 0:
    
    unlinked_aps.to_crs(proj_crs, inplace=True)
    unlinked_aps.drop(columns=['footprint_index'], inplace=True)

    # split into two groups = points linked to a parcel - run against full building dataset, points with no footprint - only run against unlinked buildings
    no_parcel = unlinked_aps[unlinked_aps['link_field'].isna()]
    parcel_link = unlinked_aps[~unlinked_aps['link_field'].isna()]

    # get all footprint_indexes (fi) from the previous steps to exclude in the next step for no parcel aps
    intersect_fi = list(set(intersections.footprint_index.tolist()))
    linking_fi = list(set(addresses.footprint_index.tolist()))

    # Bring in only those footprints that haven't yet been matched to remove matches on buildings already matched
    unlinked_footprint = footprint[~(footprint['footprint_index'].isin(linking_fi) | footprint['footprint_index'].isin(intersect_fi))]

    print('     processing unlinked geometry')
    # run the next line using only the footprints that are not already linked to an address point
    no_parcel = get_unlinked_geometry(no_parcel, unlinked_footprint, buffer_size)
    parcel_link = get_unlinked_geometry(parcel_link, footprint, buffer_size)
    
    # Grab those records that still have no link and export them for other analysis
    unmatched_points = unlinked_aps[~((unlinked_aps.index.isin(list(set(no_parcel.index.to_list())))) | (unlinked_aps.index.isin(list(set(parcel_link.index.to_list())))))]
    print(f'Number of unlinked addresses {len(unmatched_points)}')
    
    unlinked_aps = no_parcel.append(parcel_link)
    # Take only the closest linkage for unlinked geometries
    unlinked_plural = unlinked_aps['footprint_index'].map(len) > 1
    unlinked_aps.loc[unlinked_plural, "footprint_index"] = unlinked_aps[unlinked_plural][["geometry", "footprint_index"]].apply(lambda row: get_nearest_linkage(*row), axis=1)
    unlinked_aps = unlinked_aps.explode('footprint_index')
    unlinked_aps['method'] = f'{buffer_size}m_buffer'

print("Running Step 5. Merge and Export Results")

outgdf = addresses.append([intersections, addresses_bp, unlinked_aps])

print("Running Step 6: Change Point Location to Building Centroid")
print('     Creating footprint centroids')
footprint['centroid_geo'] = footprint['geometry'].apply(lambda bf: bf.representative_point())
print('     Matching address points with footprint centroids')
outgdf['out_geom'] = outgdf['footprint_index'].apply(lambda row: create_centroid_match(row, footprint['centroid_geo']))

outgdf = outgdf.set_geometry('out_geom')

outgdf.drop(columns='geometry', inplace=True)
outgdf.rename(columns={'out_geom':'geometry'}, inplace=True)
outgdf = outgdf.set_geometry('geometry')

footprint.drop(columns='centroid_geo', inplace=True)

# Find unlinked building polygons
unlinked_footprint = footprint[~footprint['footprint_index'].isin(outgdf['footprint_index'].to_list())]

# Export unlinked building polygons
unlinked_footprint.to_file(output_gpkg, layer=unmatched_poly_lyr_nme, driver='GPKG')

# Export matched address geometry
outgdf.to_file(output_gpkg, layer=matched_lyr_nme,  driver='GPKG')

# Export unmatched address geometry
unmatched_points.to_file(output_gpkg, layer=unmatched_lyr_nme, driver='GPKG')

# Export non-addressable outbuildings 
sheds.to_file(output_gpkg, layer='sheds', driver='GPKG')

end_time = datetime.datetime.now()
print(f'Start Time: {start_time}')
print(f'End Time: {end_time}')
print(f'Total Runtime: {end_time - start_time}')

print('DONE!')
