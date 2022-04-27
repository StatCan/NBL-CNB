import datetime
import os
import re
import sys
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import swifter
from dotenv import load_dotenv
from numpy.core.numeric import True_
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

'''Standardize the civic address data coming from municipal sources in NB and convert to project format, etc'''

def reproject(ingdf, output_crs):
    ''' Takes a gdf and tests to see if it is in the projects crs if it is not the funtions will reproject '''
    if ingdf.crs == None:
        ingdf.set_crs(epsg=output_crs, inplace=True)    
    elif ingdf.crs != f'epsg:{output_crs}':
        ingdf.to_crs(epsg=output_crs, inplace=True)
    return ingdf


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


# ----------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

# Path to where all civics data is downloaded to
civics_path = r'C:\projects\point_in_polygon\data\NB_data\municipal_civics'
# Per municipality list address fields in the following order civic, st name, st type, municipality
address_fields = {'Fredericton':['Nbr', 'Street_Nam', 'St_Type'],
                'Moncton':['CIVIC', 'STNAME', 'TYPE'],
                'SaintJohn':['Civic_Numb', 'Street_Name', 'English_Sign_Abrv']}

linking_data_path = Path(os.getenv('DATA_GPKG'))
linking_lyr_nme = 'parcels_cleaned'

# This output get placed in the QA GPKG for the QA step
out_path = os.getenv('BASE_PATH')
out_gpkg = Path(os.getenv('QA_GPKG'))
mun_civics_lyr_nme = os.getenv('ST_MUN_CIVICS')

proj_crs = os.getenv('PROJ_CRS')

# ----------------------------------------------------------------
# Logic

cleaned_civics = []

for f in os.listdir(civics_path):
    mun = f.split('_')[0]
    print(f'Standardizing: {mun}')
    civics = gpd.read_file(os.path.join(civics_path, f))
    civics = reproject(civics, proj_crs)

    if mun in address_fields:
        mun_ad_fields = address_fields[mun]
    else:
        print(f'Address Fields not set for {mun}. Skipping.')

    # cull records with null civic numbers
    civics = civics[~civics[mun_ad_fields[0]].isna()]

    civics['civic_num'] = civics[mun_ad_fields[0]]#.map(int) # Commented out because there are .5's in Moncton
    civics['st_nme'] = civics[mun_ad_fields[1]].str.upper().str.strip('.').str.strip(' ')
    civics['st_type'] = civics[mun_ad_fields[2]].str.upper().str.strip('.')
    
    if mun == 'SaintJohn':
        civics['source'] = 'Saint_John'
    else:
        civics['source'] = mun

    field_keep_list = ['civic_num', 'st_nme', 'st_type', 'source', 'geometry']
    civics_cols = civics.columns.tolist()
    for col in field_keep_list:
        civics_cols.remove(col)
    civics.drop(columns=civics_cols, inplace=True)
    cleaned_civics.append(civics)

cleaned_civics = pd.concat(cleaned_civics)
cleaned_civics['mun_civ_id'] = range(1, len(cleaned_civics.index)+1)
print('Joining Parcel ID to cleaned civics')
# Add parcel ID
linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme) # Load in the linking data

cleaned_civics = gpd.sjoin(cleaned_civics, linking_data[['link_field', 'geometry']], op='within', how='left')
cleaned_civics.drop(columns=['index_right'], inplace=True)

grouped = cleaned_civics.groupby('mun_civ_id', dropna=True)['mun_civ_id'].count()
grouped = grouped[grouped > 1].index.tolist()
cleaned_civics_plural_sj = cleaned_civics[cleaned_civics['mun_civ_id'].isin(grouped)]
cleaned_civics_singular = cleaned_civics[~cleaned_civics['mun_civ_id'].isin(grouped)]
cleaned_civics_plural_sj = return_smallest_match(cleaned_civics_plural_sj, linking_data, 'mun_civ_id')
cleaned_civics = cleaned_civics_singular.append(cleaned_civics_plural_sj)

print(cleaned_civics.head())
cleaned_civics.to_file(out_gpkg, layer= mun_civics_lyr_nme)
print('DONE!')
