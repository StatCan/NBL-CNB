import os
import re
import sys
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon

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
    
# ------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.path.dirname(__file__), 'environments.env'))

# Layer inputs
proj_crs = os.getenv('NT_CRS')

footprint_lyr = Path(os.getenv('NT_BF_PATH'))

ap_path = Path(os.getenv('NT_ADDRESS_PATH'))
# ap_lyr_nme = os.getenv('BC_ADDRESS_LYR_NME')
ap_add_fields = ['street_no', 'street', 'geometry']

linking_data_path = Path(os.getenv('NT_LINKING_PATH'))
# linking_lyr_nme = os.getenv('BC_LINKING_LYR_NME')
linking_ignore_columns = os.getenv('NT_LINKING_IGNORE_COLS') 

rd_gpkg = Path(os.getenv('NT_RD_GPKG'))
rd_lyr_nme = os.getenv('NT_RD_LYR_NME')
rd_use_flds = ['L_HNUMF', 'R_HNUMF', 'L_HNUML', 'R_HNUML', 'L_STNAME_C', 'R_STNAME_C', 'ROADCLASS']
# AOI mask if necessary
aoi_mask = os.getenv('NT_ODB_MASK')

# output gpkg
project_gpkg = Path(os.getenv('NT_GPKG'))
rd_crs = os.getenv('NT_RD_CRS')

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
# if type(aoi_mask) != None:
#     aoi_gdf = gpd.read_file(aoi_mask)

# aoi_gdf = aoi_gdf.loc[aoi_gdf['CSD_UID'] == '5915022']

print('Loading in linking data')
linking_data = gpd.read_file(linking_data_path, linking_ignore_columns=linking_ignore_columns) # mask=aoi_gdf)
linking_cols_drop = linking_data.columns.tolist()
linking_data['link_field'] = range(1, len(linking_data.index)+1)
linking_data = reproject(linking_data, proj_crs)
linking_cols_drop.remove('geometry')
linking_cols_drop += ['index_right']

print('Loading in address data')
if os.path.split(ap_path)[-1].endswith('.csv'):
    addresses = pd.read_csv(ap_path)
    addresses = gpd.GeoDataFrame(addresses, geometry=gpd.points_from_xy(addresses.longitude, addresses.latitude))
else:
    addresses = gpd.read_file(ap_path) #, mask=aoi_gdf)

print('Cleaning and prepping address points')

addresses = addresses[ap_add_fields]
addresses = reproject(addresses, proj_crs)
addresses = gpd.sjoin(addresses, linking_data, op='within')
addresses.drop(columns=linking_cols_drop, inplace=True)
for f in ['index_right', 'index_left']:
    if f in addresses.columns.tolist():
        addresses.drop(columns=f, inplace=True)

addresses = addresses[addresses["street_no"] != 'RITE OF WAY']
addresses["suffix"] = addresses["street_no"].map(lambda val: re.sub(pattern="\\d+", repl="", string=val, flags=re.I))
addresses["number"] = addresses["street_no"].map(lambda val: re.sub(pattern="[^\\d]", repl="", string=val, flags=re.I)).map(int)
addresses['street'] = addresses['street'].str.upper()
print('Exporting cleaned dataset')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')
del addresses

print('Loading in road data')
roads = gpd.GeoDataFrame.from_features(records(rd_gpkg, rd_use_flds, layer=rd_lyr_nme, driver='GPKG')) # Load in only needed fields
roads.set_crs(epsg=rd_crs, inplace=True)

print('Cleaning and prepping road data')
# Clean Roads to match the address format
# Remove all the unknown named roads
roads = roads[(roads['L_STNAME_C'] != 'Unknown') | (roads['R_STNAME_C'] != 'Unknown')]
# Remove all the winder roads
roads = roads[(roads['ROADCLASS'] != 'Winter')]

# Remove additional punctuation that is no longer needed
roads['l_nme_cln'] = roads.L_STNAME_C.str.replace('[^\w\s-]', '')
roads['r_nme_cln'] = roads.R_STNAME_C.str.replace('[^\w\s-]', '')

# Correct road type abbreviations
roads['l_nme_cln'] = roads['l_nme_cln'].apply(lambda row: str_type_cln(row, type_corr_dict))

# Drop unecessary columns
roads.drop(columns=['L_STNAME_C', 'R_STNAME_C'],  inplace=True)

print('Exporting cleaned dataset')
roads.to_file(project_gpkg, layer='roads_cleaned', driver='GPKG')
del roads

print('Loading in footprint data')
footprint = gpd.read_file(footprint_lyr)# , mask=aoi_gdf)

print('Cleaning and prepping footprint data')
# footprint = explode(footprint) # Remove multipart polygons convert to single polygons
footprint['area'] = footprint['geometry'].area
footprint = footprint.loc[footprint.area >= 20.0] # Remove all buildings with an area of less than 20m**2
footprint = footprint.reset_index()
footprint.rename(columns={'index':'bf_index'}, inplace=True)
footprint.set_index(footprint['bf_index'])
footprint = reproject(footprint, proj_crs)

footprint['centroid_geo'] = footprint['geometry'].apply(lambda pt: pt.centroid)
footprint = footprint.set_geometry('centroid_geo')

footprint = gpd.sjoin(footprint, linking_data, how='left', op='within')
footprint.drop(columns=linking_cols_drop, inplace=True)

footprint = footprint.set_geometry('geometry')
footprint.drop(columns=['centroid_geo'], inplace=True)

for f in ['index_right', 'index_left']:
    if f in footprint.columns.tolist():
        footprint.drop(columns=f, inplace=True)

print('Exporting cleaned dataset')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')

print('DONE!')
[
    'ABBEY', 'ACRES', 'ALLÉE', 'ALLEY', 'AUT', 'AVE', 'AV', 'BAY', 'BEACH', 'BEND', 'BLVD', 'BOUL', 'BYPASS', 'BYWAY', 'CAMPUS', 'CAPE', 'CAR', 'CARREF', 'CTR', 'C', 'CERCLE', 'CHASE', 'CH', 'CIR', 'CIRCT', 'CLOSE', 'COMMON', 'CONC', 'CRNRS', 'CÔTE', 'COUR', 'COURS', 'CRT', 'COVE', 'CRES', 'CROIS', 'CROSS', 'CDS', 'DALE', 'DELL', 'DIVERS', 'DOWNS', 'DR', 'ÉCH', 'END', 'ESPL', 'ESTATE', 'EXPY', 'EXTEN',
    'PINES','PL', 'PLACE', 'PLAT', 'PLAZA', 'PT', 'POINTE', 'PORT', 'PVT', 'PROM', 'QUAI', 'QUAY', 'RAMP', 'RANG', 'RG', 'RIDGE', 'RISE', 'RD', 'RDPT', 'RTE', 'ROW', 'RUE', 'RLE', 'RUN', 'SENT', 'SQ', 'ST', 'SUBDIV', 'TERR', 'TSSE', 'THICK', 'TOWERS', 'TLINE', 'TRAIL', 'TRNABT', 'VALE', 'VIA', 'VIEW', 'VILLGE', 'VILLAS', 'VISTA', 'VOIE', 'WALK', 'WAY', 'WHARF', 'WOOD', 'WYND'
]