import datetime
import os
import re
import string
import sys
from pathlib import Path
from math import isnan
import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from sqlalchemy import column
import swifter
from dotenv import load_dotenv
from numpy.core.numeric import True_
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

'''
Script to test integration of municipal civic sources to get higher confidence matches in areas where they are available

To start get counts of the number of addresses per parcel for each dataset and highlight where there counts are different in Fredericton
'''

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


def count_setter(parcel_idents, ap_parcel_counts, mc_parcel_counts):
    '''Returns the parcel relationship counts for the given record based on the counts of the parcel linkages in the fc and ap datasets'''
    count_lists = []
    for parcel_ident in parcel_idents:
        if isnan(parcel_ident):
            continue

        ap_count = ap_parcel_counts[ap_parcel_counts.index == parcel_ident].tolist()
        mc_count = mc_parcel_counts[mc_parcel_counts.index == parcel_ident].tolist()
        
        if len(mc_count) > 0:
            mc_count = mc_count[0]
        else:
            mc_count = 0

        if len(ap_count) > 0:
            ap_count = ap_count[0]
        else:
            ap_count = 0

        count_lists.append([parcel_ident, ap_count, mc_count])   
    
    return count_lists
      

# ------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

proj_crs = os.getenv('PROJ_CRS')

linking_data_path = Path(os.getenv('DATA_GPKG'))
linking_lyr_nme = 'parcels_cleaned'

ap_path = Path(os.getenv('DATA_GPKG'))
ap_lyr_nme = 'addresses_cleaned'

# municipal civics address comparison (test for Fredericton)

fred_civics_path = r'C:\projects\point_in_polygon\data\NB_data\municipal_civics\Fredericton_Geocoded_Civics.geojson'

output_gpkg = r'C:\projects\point_in_polygon\data\NB_data\qc_qa_tests.gpkg'

# ------------------------------------
#  Logic

print('Loading in data')
addresses = gpd.read_file(ap_path, layer=ap_lyr_nme)
fred_civics = gpd.read_file(fred_civics_path)
# footprints = gpd.read_file(bf_path, layer=bf_lyr_nme)
parcels = gpd.read_file(linking_data_path, layer=linking_lyr_nme)
# footprints.to_crs(crs=proj_crs, inplace=True)
parcels = reproject(parcels, proj_crs)
addresses = reproject(addresses, proj_crs)

# Prep and clean municipal civics
fred_civics = reproject(fred_civics, proj_crs)
fred_civics['fc_id'] = fred_civics.index
fred_civics = gpd.sjoin(fred_civics, parcels[['link_field', 'geometry']], op='within', how='left')

# Deal with duplications in the address  layer caused by the spatial join. Take the smallest parcel as assumed to be the most accurate
grouped = fred_civics.groupby('fc_id', dropna=True)['fc_id'].count()
grouped = grouped[grouped > 1].index.tolist()
fred_civics_plural_sj = fred_civics[fred_civics['fc_id'].isin(grouped)]
fred_civics_singular = fred_civics[~fred_civics['fc_id'].isin(grouped)]

fred_civics_plural_sj = return_smallest_match(fred_civics_plural_sj, parcels, 'fc_id')
fred_civics = fred_civics_singular.append(fred_civics_plural_sj)
fred_civics.drop(columns=['index_right'], inplace=True)

# Group nb addresses
grouped_ap = addresses.groupby('link_field', dropna=True)['link_field'].count()

# Group municipal civics
grouped_fc = fred_civics.groupby('link_field', dropna=True)['link_field'].count()

point_counts = pd.DataFrame(count_setter(parcels['link_field'].tolist(), grouped_ap, grouped_fc), columns=['link_field',  'nb_ap_count', 'fc_ap_count'])
parcels = pd.merge(parcels, point_counts, how='outer', on='link_field')
#parcels.drop(columns=['link_field_fc_civic'], inplace=True)
parcels.to_file(output_gpkg, layer='parcel_mc_counts')

print('DONE!')
