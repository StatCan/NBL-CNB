import datetime
import sys
import shapely
import os
import re
import string
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from math import pi
from shapely.geometry import MultiLineString, Polygon, Point
from shapely.validation import make_valid
from polygon_cutter import PolygonCutter

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

# ------------------------------------------------------------------------------------------------
# Functions

def reproject(ingdf: gpd.GeoDataFrame, output_crs: int) -> gpd.GeoDataFrame:
    ''' Takes a gdf and tests to see if it is in the projects crs if it is not the funtions will reproject '''
    if ingdf.crs == None:
        ingdf.set_crs(epsg=output_crs, inplace=True)    
    elif ingdf.crs != f'epsg:{output_crs}':
        ingdf.to_crs(epsg=output_crs, inplace=True)
    return ingdf


def getXY(pt: Point) -> tuple:
    return (pt.x, pt.y)


def records(filename, usecols, **kwargs):
    ''' Allows for import of file with only the desired fields must use from_features for importing output into geodataframe'''
    with fiona.open(filename, **kwargs) as source:
        for feature in source:
            f = {k: feature[k] for k in ['id', 'geometry']}
            f['properties'] = {k: feature['properties'][k] for k in usecols}
            yield f


def return_smallest_match(ap_matches, parcel_df, unique_id):
    '''Takes plural matches of buildings or address points and compares them against the size of the matched parcel. Returns only the smallest parcel that was matched'''
    ap_matches['ap_match_id'] = range(1, len(ap_matches.index)+1)
    o_ids = []
    for rid in list(set(ap_matches[unique_id].tolist())):
        rid_matches = ap_matches[ap_matches[unique_id] == rid]
        rid_ids = list(set(rid_matches['link_field'].tolist()))
        match_parcels = parcel_df[parcel_df['link_field'].isin(rid_ids)]
        match_parcels.sort_values(by=['AREA'], inplace=True, ascending=True)
        min_parcel_link = match_parcels['link_field'].tolist()[0]
        o_ids.append(rid_matches[rid_matches['link_field'] == min_parcel_link].ap_match_id.tolist()[0])
    ap_matches = ap_matches[ap_matches['ap_match_id'].isin(o_ids)]
    ap_matches.drop(columns=['ap_match_id'], inplace=True)
    return ap_matches
    

def shed_flagging(footprint_gdf, address_gdf, linking_gdf) -> gpd.GeoDataFrame:
    '''
    Methodology for flagging buildings as sheds. Sheds meaning unaddressable outbuildings
    '''
    
    def find_sheds( bf_data, ap_count, bf_area_field='bf_area', bf_index_field='bf_index', bp_threshold=20, min_adressable_area=50, max_shed_size=100) -> list:
        '''
        returns a list of all bf_indexes that should be flagged as sheds and should be considered unaddressable.
        take the difference from the counts of each type of record in the parcel and flag the number of smallest
        buildings that coorespond with the difference value
        '''
        bf_count = len(bf_data)
        
        # If either is equal to zero this method will not help select out sheds
        if (ap_count == 0) or (bf_count in [0,1]):
            return []

        # Sizing is different in trailer parks so deal with these differently
        if bf_count > bp_threshold:
            # do just the tiny building check as the min max between home and shed in these areas overlaps
            sheds = bf_data.loc[bf_data[bf_area_field] < min_adressable_area]
            shed_indexes = sheds[bf_index_field].values.tolist() # convert to list of indexes
            return shed_indexes

        # Take out the tiny buildings under 50m2 and prelabel them as sheds then take remainder and test count vs count
        sheds = pd.DataFrame(bf_data.loc[bf_data[bf_area_field] < min_adressable_area])
        bf_data = bf_data.loc[(bf_data[bf_area_field] > min_adressable_area)]

        bf_count = len(bf_data) # reset bf_count because we changed the # of buildings in bf_data

        ap_bf_diff = bf_count - ap_count # how many more bf's there are than address points in the parcel
        sheds = pd.concat([sheds, bf_data.sort_values(bf_area_field, ascending=True).head(ap_bf_diff)], axis=0, join='outer') # sort the smallest to the top then take the top x rows based on ap_bf_diff value 
        
        sheds = sheds[sheds[bf_area_field] <= max_shed_size] # remove things from the output that are unlikly to be sheds >= 100m2

        shed_indexes = sheds[bf_index_field].values.tolist() # convert to list of indexes
        return shed_indexes

    # Start by finding all the perfectly round buildings and labelling them as sheds size doesn't matter here.
    footprint_gdf['perimiter'] = footprint_gdf['geometry'].apply(lambda x: round(x.length, 2))
    footprint_gdf['C'] = footprint_gdf.apply(lambda c: (4*pi*c['bf_area'])/(c['perimiter']*c['perimiter']), axis=1)
    # separate out the round sheds from rest of the 
    round_sheds = footprint_gdf[footprint_gdf['C'] >= 0.98]
    footprint_gdf = footprint_gdf[footprint_gdf['C'] < 0.98]
    footprint_gdf.drop(columns=['C'], inplace=True)
    round_sheds.drop(columns=['C'], inplace=True)
    
    # Of the remaining group, count, slice
    adp_parcel_linkages = address_gdf.groupby('link_field', dropna=True)['link_field'].count()
    bf_parcel_linkages = footprint_gdf.groupby('link_field', dropna=True)['link_field'].count()

    # Return only cases where the bf count is higher than the adp count
    adp_parcel_l_bf = adp_parcel_linkages[adp_parcel_linkages.index.isin(bf_parcel_linkages.index.tolist())]
    bf_parcel_l_ap = bf_parcel_linkages[bf_parcel_linkages.index.isin(adp_parcel_linkages.index.tolist())]

    bf_parcel_l_ap = pd.DataFrame(bf_parcel_l_ap)
    bf_parcel_l_ap.rename(columns={ bf_parcel_l_ap.columns[0]: "bf_count"}, inplace=True)

    adp_parcel_l_bf = pd.DataFrame(adp_parcel_l_bf)
    adp_parcel_l_bf.rename(columns={adp_parcel_l_bf.columns[0]: "ap_count"}, inplace=True)

    linking_gdf = linking_gdf.loc[linking_gdf['link_field'].isin(bf_parcel_l_ap.index.tolist())]
    linking_gdf['shed_list'] = linking_gdf['link_field'].apply(lambda x: find_sheds(footprint_gdf[footprint_gdf['link_field'] == x], adp_parcel_l_bf[adp_parcel_l_bf.index == x].ap_count.tolist()[0]))
    shed_indexes = [ i for l in linking_gdf['shed_list'].tolist() for i in l ] # item for sublist in t for item in sublist: t being the shed_list list

    shed_gdf = footprint_gdf[footprint_gdf['bf_index'].isin(shed_indexes)]
    footprint_gdf = footprint_gdf.loc[~footprint_gdf['bf_index'].isin(shed_indexes)]

    shed_gdf['shed_flag'] = True
    round_sheds['shed_flag'] = True
    footprint_gdf['shed_flag'] = False
    footprint_gdf = footprint_gdf.append([shed_gdf, round_sheds])
    return footprint_gdf


def ValidateGeometry(input_geometry: shapely.geometry) -> gpd.GeoSeries:
            '''Checks if input geometry is valid and if invalid attempts to make it valid accepts Geodataframes and Geoseries'''
            if type(input_geometry) == gpd.GeoSeries:
                input_geometry = input_geometry.apply(lambda geom: make_valid(geom))
            if type(input_geometry) == gpd.GeoDataFrame:
                input_geometry = input_geometry['geometry'].apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
            return input_geometry


# ------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

proj_crs = os.getenv('PROJ_CRS')

footprint_lyr = Path(os.getenv('BF_PATH'))
footprint_lyr_name = os.getenv('BF_LYR_NME')

ap_path = Path(os.getenv('ADDRESS_PATH'))
ap_lyr_nme = os.getenv('ADDRESS_LAYER')

ap_add_fields = ['CIVIC_NUM', 'STREET', 'ST_TYPE_E', 'ADDR_DESC', 'geometry'] # geoNB fields ['CIVIC_NUM', 'STREET_NAME', 'ST_TYPE_CD', 'ST_NAME_COMPLETE', 'geometry']
ap_type_cds = Path(os.getenv('ADDRESS_TYPE_CODES'))

linking_data_path = Path(os.getenv('LINKING_PATH'))
linking_lyr_nme = os.getenv('LINKING_LYR_NME')

linking_ignore_columns = os.getenv('LINKING_IGNORE_COLS') 

# AOI mask if necessary
aoi_mask = os.getenv('AOI_MASK')

# output gpkg
project_gpkg = Path(os.getenv('DATA_GPKG'))

# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
if aoi_mask != None:
    aoi_gdf = gpd.read_file(aoi_mask)

print('Loading in linking data')
linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme, linking_ignore_columns=linking_ignore_columns, mask=aoi_gdf)
linking_data = reproject(linking_data, proj_crs)
linking_cols_drop = linking_data.columns.tolist()
linking_data['link_field'] = range(1, len(linking_data.index)+1)
linking_data['AREA'] = linking_data['geometry'].area
linking_data = linking_data[linking_data['AREA'] > 101]

for col in ['geometry', 'Pan_Int', 'Location']:
    if col in linking_cols_drop:
        linking_cols_drop.remove(col)

linking_data.drop(columns=linking_cols_drop, inplace=True)

linking_data.to_file(project_gpkg, layer='parcels_cleaned', driver='GPKG')

print('Loading in address data')
if os.path.split(ap_path)[-1].endswith('.csv'):
    addresses = pd.read_csv(ap_path)
    addresses = gpd.GeoDataFrame(addresses, geometry=gpd.points_from_xy(addresses.longitude, addresses.latitude))
else:
    addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf)

print('Cleaning and prepping address points')

# addresses = addresses[ap_add_fields]
addresses = reproject(addresses, proj_crs)
addresses = gpd.sjoin(addresses, linking_data[['link_field', 'geometry']], op='within', how='left')

# Deal with duplications in the address  layer caused by the spatial join. Take the smallest parcel as assumed to be the most accurate
grouped = addresses.groupby('CIV_ID', dropna=True)['CIV_ID'].count()
grouped = grouped[grouped > 1].index.tolist()
addresses_plural_sj = addresses[addresses['CIV_ID'].isin(grouped)]
addresses_singular = addresses[~addresses['CIV_ID'].isin(grouped)]
addresses_plural_sj = return_smallest_match(addresses_plural_sj, linking_data, 'CIV_ID')
addresses = addresses_singular.append(addresses_plural_sj)

for f in ['index_right', 'index_left', 'nbl_objectid', 'OBJECTID', 'DESCRIPT', 'ALT_ACCESS', 'COLL_MTHD', 'CREATED', 'MODIFIED', 'ST_TYPE_F', 'RD_SIDE_E', 'RD_SIDE_F', 'ST_DIR_E', 'ST_DIR_F',  'ADD_TYPE_E', 'ADD_TYPE_F', 'NUM_SUFFIX']:
    if f in addresses.columns.tolist():
        addresses.drop(columns=f, inplace=True)

addresses['a_id'] = addresses.index
addresses["number"] = addresses[ap_add_fields[0]]
addresses['street'] = addresses[ap_add_fields[1]]
addresses['stype_en'] =addresses[ap_add_fields[2]].str.upper()

# addresses = addresses.append(none_stype)
addresses.drop(columns=[ap_add_fields[0], ap_add_fields[1], ap_add_fields[2]], inplace=True)

print('Exporting cleaned address dataset')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')

print('Loading in footprint data')
footprint = gpd.read_file(footprint_lyr, layer=footprint_lyr_name ,mask=aoi_gdf)

footprint = reproject(footprint, proj_crs)

footprint['geometry'] = ValidateGeometry(footprint['geometry'])

# Cut polygons by parcels
cutter = PolygonCutter(footprint, linking_data, crs=4326, proj_crs=int(proj_crs))
footprint = cutter.bp

print('Cleaning and prepping footprint data')

footprint['bf_area'] = round(footprint['geometry'].area, 2)

footprint = footprint.reset_index()

# Ensure field and projection consistency
footprint.rename(columns={'index':'bf_index'}, inplace=True)
footprint.set_index(footprint['bf_index'])
footprint = reproject(footprint, proj_crs)
linking_data = reproject(linking_data, proj_crs)

footprint['centroid_geo'] = footprint['geometry'].apply(lambda pt: pt.centroid)
footprint = footprint.set_geometry('centroid_geo')
footprint = gpd.sjoin(footprint, linking_data[['link_field', 'geometry']], how='left', op='within')

grouped_bf = footprint.groupby('bf_index', dropna=True)['bf_index'].count()
grouped_bf = grouped_bf[grouped_bf > 1].index.tolist()
footprint_plural_sj = footprint[footprint['bf_index'].isin(grouped_bf)]
footprint_singular = footprint[~footprint['bf_index'].isin(grouped_bf)]
footprint_plural_sj = return_smallest_match(footprint_plural_sj, linking_data, 'bf_index')
footprint = footprint_singular.append(footprint_plural_sj)

footprint = shed_flagging(footprint, addresses, linking_data)

footprint = footprint.set_geometry('geometry')
footprint.drop(columns=['centroid_geo'], inplace=True)

for f in ['index_right', 'index_left', 'OBJECTID', 'fid']:
    if f in footprint.columns.tolist():
        footprint.drop(columns=f, inplace=True)

print('Exporting cleaned dataset')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')

end_time = datetime.datetime.now()
print(f'Start Time: {start_time}')
print(f'End Time: {end_time}')
print(f'Total Runtime: {end_time - start_time}')
print('DONE!')
