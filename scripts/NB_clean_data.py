import os
import re
import sys
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
from numpy.core.numeric import True_
import pandas as pd
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo
from dotenv import load_dotenv
import datetime

# ------------------------------------------------------------------------------------------------
# Functions

def explode(ingdf):
    # not one of Jesse's. To solve multipolygon issue
    indf = ingdf
    outdf = gpd.GeoDataFrame(columns=indf.columns)
    for idx, row in indf.iterrows():
        
        if type(row.geometry) == Polygon:
            outdf = outdf.append(row,ignore_index=True)
        if type(row.geometry) == MultiPolygon:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row]*recs,ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom,'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf,ignore_index=True)
    return outdf


def reproject(ingdf, output_crs):
    ''' Takes a gdf and tests to see if it is in the projects crs if it is not the funtions will reproject '''
    if ingdf.crs == None:
        ingdf.set_crs(epsg=output_crs, inplace=True)    
    elif ingdf.crs != f'epsg:{output_crs}':
        ingdf.to_crs(epsg=output_crs, inplace=True)
    return ingdf


def getXY(pt):
    return (pt.x, pt.y)


def records(filename, usecols, **kwargs):
    ''' Allows for importation of file with only the desired fields must use from_features for importing output into geodataframe'''
    with fiona.open(filename, **kwargs) as source:
        for feature in source:
            f = {k: feature[k] for k in ['id', 'geometry']}
            f['properties'] = {k: feature['properties'][k] for k in usecols}
            yield f


def str_type_cln(street_name, correction_dict):
    '''Cleans the street types so that they are standardized across all datasets returns the corrected street type in upper case'''
    street_name = street_name.upper()
    street_split = street_name.split()
    
    # If single word or empty return the name as is
    if (street_split == 1 or street_split == 0):
        return street_name

    s_type = street_split[-1]
    type_index = street_split.index(s_type)
    
    # If last word is a direction take the second last word
    if (len(s_type) == 1 or len(s_type) == 2) and (s_type in ['N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'O', 'SO']):
        s_type = street_split[-2]
        type_index = street_split.index(s_type)
    
    # ensure that street type conforms to the correct appreviation as outlined in the list
    if s_type in correction_dict:
        s_type = correction_dict[s_type]
    
    #Put the cleaned street name back together
    street_split[type_index] = s_type
    cleaned_name = " ".join(street_split)
    
    return cleaned_name
    

def road_partitioner(address):
    '''Takes a road string which possibly containes name, type and direction and converts it into a list of parts based off of master lists of road types'''
    
    def determiner(in_string, check_list):
        ''' Determines if string is in input list. If it is then returns the value as a string else it will return np.nan'''
        output = [i for i in check_list if in_string == i]
        
        if len(output) == 0:
            return np.nan
        
        return output[0]

    type_abbrev = ['ABBEY', 'ACRES', 'ALLÉE', 'ALLEY', 'AUT', 'AVE', 'AV', 'BAY', 'BEACH', 'BEND', 'BLVD', 'BOUL', 'BYPASS', 'BYWAY', 'CAMPUS', 'CAPE', 'CAR', 
            'CARREF', 'CTR', 'C', 'CERCLE', 'CHASE', 'CH', 'CIR', 'CIRCT', 'CLOSE', 'COMMON', 'CONC', 'CRNRS', 'CÔTE', 'COUR', 'COURS', 'CRT', 'COVE', 'CRES', 
            'CROIS', 'CROSS', 'CDS', 'DALE', 'DELL', 'DIVERS', 'DOWNS', 'DR', 'ÉCH', 'END', 'ESPL', 'ESTATE', 'EXPY', 'EXTEN', 'HWY', 'PINES','PL', 'PLACE', 'PLAT', 
            'PLAZA', 'PT', 'POINTE', 'PORT', 'PVT', 'PROM', 'QUAI', 'QUAY', 'RAMP', 'RANG', 'RG', 'RIDGE', 'RISE', 'RD', 'RDPT', 'RTE', 'ROW', 'RUE', 'RLE', 
            'RUN', 'SENT', 'SQ', 'ST', 'SUBDIV', 'TERR', 'TSSE', 'THICK', 'TOWERS', 'TLINE', 'TRAIL', 'TRNABT', 'VALE', 'VIA', 'VIEW', 'VILLGE', 'VILLAS', 
            'VISTA', 'VOIE', 'WALK', 'WAY', 'WHARF', 'WOOD', 'WYND']
    directions = [' N ', ' S ', ' E ', ' W ', ' NE ', ' SE ', ' NW ', ' SW ', ' O ', ' NO ', ' SO ']

    # If available find the roads alt name in the adress and assign it to the correct vars. Slice out the address after
    alt_name = np.nan
    alt_type = np.nan
    alt_name_full = np.nan

    if address.find('(') != -1:
        s_index = address.index('(')+1
        c_index = address.index(')')
        alt_full = address[s_index : c_index].split(' ')
        alt_name_full = address[s_index : c_index]
        alt_type =  determiner(alt_full[-1], type_abbrev)
        if type(alt_type) == str: del alt_full[-1]

        alt_name = ' '.join(alt_full)

        # Slice out the alt string from the address
        address = address[0 : address.index('(') : ] + address[address.index(')') + 1 : :].rstrip() 
    
    # Split into component parts and filter out 0 len strings
    add_parts = address.split(' ')
    add_parts = list(filter(len, add_parts))

    # Grab the directio from the end of the road
    direction = determiner(add_parts[-1], directions)
    if type(direction) == str: del add_parts[-1]
    
    # Grab the road type
    rtype = determiner(add_parts[-1], type_abbrev)
    if type(rtype) == str: del add_parts[-1]    

    # Compile the full road name
    str_nme = ' '.join(add_parts)
    str_nme_full = []
    for f in [str_nme, rtype, direction]:
        if type(f) == str:
            str_nme_full.append(f)
    str_nme_full = ' '.join(str_nme_full)

    return [str_nme, rtype, direction, alt_name, alt_type, alt_name_full, str_nme_full]    
# ------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

geo_crs = os.getenv('CRS')
proj_crs = os.getenv('PROJ_CRS')

footprint_lyr = Path(os.getenv('BF_PATH'))

ap_path = Path(os.getenv('ADDRESS_PATH'))
ap_lyr_nme = os.getenv('ADDRESS_LAYER')

ap_add_fields = ['CIVIC_NUM', 'STREET', 'ST_TYPE_E', 'ADDR_DESC', 'geometry'] # geoNB fields ['CIVIC_NUM', 'STREET_NAME', 'ST_TYPE_CD', 'ST_NAME_COMPLETE', 'geometry']
ap_type_cds = Path(os.getenv('ADDRESS_TYPE_CODES'))

linking_data_path = Path(os.getenv('LINKING_PATH'))
linking_lyr_nme = os.getenv('LINKING_LYR_NME')

linking_ignore_columns = os.getenv('LINKING_IGNORE_COLS') 

rd_gpkg = Path(os.getenv('RD_GPKG'))
rd_lyr_nme = os.getenv('RD_LYR_NME')
rd_use_flds = ['L_HNUMF', 'R_HNUMF', 'L_HNUML', 'R_HNUML', 'L_STNAME_C', 'R_STNAME_C', 'ROADCLASS']
# AOI mask if necessary
aoi_mask = Path(os.getenv('AOI_MASK'))

# output gpkg
project_gpkg = Path(os.getenv('DATA_GPKG'))
rd_crs = os.getenv('RD_CRS')

# Road name correction dictionary
type_corr_dict = {
    'CR' : 'CRES',
    'LN' : 'LANE', 
    'CRESCENT': 'CRES', 
    'AVENUE' : 'AVE',
    'BOULEVARD' : 'BLVD',
    'DRIVE' : 'DR', 
    'LANE' : 'LN', 
    'PLACE' : 'PL',
    'CENTRE' : 'CTR',
    'CIRCLE' : 'CIR', 
    'CIRCUIT' : 'CIRCT',
    'CHEMIN' : 'CH', 
    'CONCESSION' : 'CONC',
    'COURT' : 'CRT',
    'DRIVE' : 'DR',
    'HIGHWAY' : 'HWY',
    'PLACE' : 'PL',
    'POINT' : 'PT',
    'PRIVATE' : 'PVT',
    'PROMINADE' : 'PROM',
    'RANGE' : 'RG',
    'ROAD' :'RD',
    'ROUTE' : 'RTE',
    'STREET' : 'ST',
    'SUBDIVISION' : 'SUB',
    'TERRACE' : 'TSSE',
}
master_types = ['ABBEY', 'ACRES', 'ALLÉE', 'ALLEY', 'AUT', 'AVE', 'AV', 'BAY', 'BEACH', 'BEND', 'BLVD', 'BOUL', 'BYPASS', 'BYWAY', 'CAMPUS', 'CAPE', 'CAR', 
            'CARREF', 'CTR', 'C', 'CERCLE', 'CHASE', 'CH', 'CIR', 'CIRCT', 'CLOSE', 'COMMON', 'CONC', 'CRNRS', 'CÔTE', 'COUR', 'COURS', 'CRT', 'COVE', 'CRES', 
            'CROIS', 'CROSS', 'CDS', 'DALE', 'DELL', 'DIVERS', 'DOWNS', 'DR', 'ÉCH', 'END', 'ESPL', 'ESTATE', 'EXPY', 'EXTEN', 'PINES','PL', 'PLACE', 'PLAT', 
            'PLAZA', 'PT', 'POINTE', 'PORT', 'PVT', 'PROM', 'QUAI', 'QUAY', 'RAMP', 'RANG', 'RG', 'RIDGE', 'RISE', 'RD', 'RDPT', 'RTE', 'ROW', 'RUE', 'RLE', 
            'RUN', 'SENT', 'SQ', 'ST', 'SUBDIV', 'TERR', 'TSSE', 'THICK', 'TOWERS', 'TLINE', 'TRAIL', 'TRNABT', 'VALE', 'VIA', 'VIEW', 'VILLGE', 'VILLAS', 
            'VISTA', 'VOIE', 'WALK', 'WAY', 'WHARF', 'WOOD', 'WYND']
# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
if type(aoi_mask) != None:
    aoi_gdf = gpd.read_file(aoi_mask)

print('Loading in linking data')
linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme, linking_ignore_columns=linking_ignore_columns, mask=aoi_gdf)
linking_cols_drop = linking_data.columns.tolist()
linking_data['link_field'] = range(1, len(linking_data.index)+1)
linking_data = reproject(linking_data, proj_crs)
linking_cols_drop.remove('geometry')
# linking_cols_drop += ['index_right']
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
addresses = gpd.sjoin(addresses, linking_data, op='within', how='left')

addresses.drop(columns=['index_right'], inplace=True)

for f in ['index_right', 'index_left']:
    if f in addresses.columns.tolist():
        addresses.drop(columns=f, inplace=True)

addresses["number"] = addresses[ap_add_fields[0]].map(int)
addresses['street'] = addresses[ap_add_fields[1]].str.upper()
addresses.drop(columns=[ap_add_fields[0], ap_add_fields[1]], inplace=True)

print('Exporting cleaned dataset')

addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')
del addresses

# print('Loading in road data')
# roads = gpd.GeoDataFrame.from_features(records(rd_gpkg, rd_use_flds, layer=rd_lyr_nme, driver='GPKG'), mask=aoi_gdf) # Load in only needed fields
# roads.set_crs(epsg=rd_crs, inplace=True)

# roads['uid'] = range(1, len(roads.index)+1)

# roads = roads[(roads['L_STNAME_C'] != 'Unknown') | (roads['R_STNAME_C'] != 'Unknown')]
# # Remove all the winter roads
# roads = roads[(roads['ROADCLASS'] != 'Winter')]

# # Remove additional punctuation that is no longer needed
# for punc in [',', '.']:
#     roads['L_STNAME_C'] = roads.L_STNAME_C.str.replace(punc, '')
#     roads['R_STNAME_C'] = roads.R_STNAME_C.str.replace(punc, '')

# roads['l_nme_cln'] = roads['L_STNAME_C']
# roads['R_nme_cln'] = roads['R_STNAME_C']

# # Correct road type abbreviations
# # print(roads[roads.uid == 4613])
# # roads = roads[roads.uid == 4613]

# roads['l_nme_cln'] = roads['l_nme_cln'].apply(lambda row: str_type_cln(row, type_corr_dict))

# roads['road_parts'] = roads['l_nme_cln'].apply(lambda s_name: road_partitioner(s_name))
# roads['STREET_NAME_FULL'] = roads['road_parts'].apply(lambda x: x[6])
# roads['STREET_NAME'] = roads['road_parts'].apply(lambda x: x[0])
# roads['STREET_TYPE'] = roads['road_parts'].apply(lambda x: x[1])
# roads['STREET_DIRECTION'] = roads['road_parts'].apply(lambda x: x[2])
# roads['ALT_NAME_FULL'] = roads['road_parts'].apply(lambda x: x[5])
# roads['ALT_NAME'] =  roads['road_parts'].apply(lambda x: x[3])
# roads['ALT_TYPE'] =  roads['road_parts'].apply(lambda x: x[4])

# # Drop unecessary columns
# roads.drop(columns=['L_STNAME_C', 'R_STNAME_C', 'road_parts'],  inplace=True)

# print('Exporting cleaned dataset')
# roads.to_file(project_gpkg, layer='roads_cleaned', driver='GPKG')
# del roads

print('Loading in footprint data')
footprint = gpd.read_file(footprint_lyr, mask=aoi_gdf)

footprint = reproject(footprint, proj_crs)

print('Cleaning and prepping footprint data')
# footprint = explode(footprint) # Remove multipart polygons convert to single polygons
footprint['area'] = footprint['geometry'].area
# footprint = footprint.loc[footprint.area >= 20.0] # Remove all buildings with an area of less than 20m**2
footprint = footprint.reset_index()
footprint.rename(columns={'index':'bf_index'}, inplace=True)
footprint.set_index(footprint['bf_index'])
footprint = reproject(footprint, proj_crs)

footprint['centroid_geo'] = footprint['geometry'].apply(lambda pt: pt.centroid)
footprint = footprint.set_geometry('centroid_geo')

footprint = gpd.sjoin(footprint, linking_data, how='left', op='within')

footprint = footprint.set_geometry('geometry')
footprint.drop(columns=['centroid_geo'], inplace=True)

for f in ['index_right', 'index_left']:
    if f in footprint.columns.tolist():
        footprint.drop(columns=f, inplace=True)

print('Exporting cleaned dataset')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')

end_time = datetime.datetime.now()
print(f'Start Time: {start_time}')
print(f'End Time: {end_time}')
print(f'Total Runtime: {end_time - start_time}')
print('DONE!')