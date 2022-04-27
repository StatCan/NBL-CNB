import datetime
from lib2to3.pgen2 import driver
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

''' This script is to assign a confidence score to the matches made in the matching master script. To do this several difference sources are compiled and compared to the 
matches as a way to test for consistency across the datasets. 

The initial list of sources for this confidence test:

- Point polygon parcel relationship
- NAR
- Municipal level civic address points
- Underlying parcel location field 

'''

def civics_flag_builder(civic_num, str_nme, str_type, mun_civics, civics_number_field='civic_num', civics_sname_field='st_nme', civics_stype_field='st_type'):
    '''Creates the confidence flags for a match and returns the following output:
    
    1: Address value matches a civic address that fall in same parcel
    0: Address value does not match civic thaat fall in same parcel
    -1: No civic value in parcel or no underlying parcel to compare
    
    Inputs should be prefiltered to only the records associated with the adp and parcel in question
    str_type is currently unused but can be added in in the future
    '''
    # if no municipal civics are present return -1
    if len(mun_civics) == 0:
        return -1
    
    check_address = mun_civics.loc[(mun_civics[civics_number_field].map(int) == int(civic_num)) & (mun_civics[civics_sname_field] == str_nme)]
    if len(check_address) == 0:
        # as there was no match on street name return 0
        return 0
    
    if len(check_address) >= 1:
        return 1

    print(civic_num, str_nme)
    print(check_address)
    sys.exit()


def parcel_location_flag_builder(address_row, parcel_row):
    '''
    Compares the address data for address points against linked parcels (if available). A full, partial, or false match is determined and a flag of the correct type is
    placed on the record. 

    outputs the following flags:

    0 - Address point and parcel address match do not match
    1 - Address point and parcel address match
    -1 - Underlying parcel issue (either no underlying parcel or no valid underlying address)

    '''
    
    # For cases where there are no underlying parcel but should be filtered out before being put through this function
    if len(parcel_row) == 0:
        return -1
    
    a_list = address_row.tolist()
    p_list = parcel_row.iloc[0].tolist()

    # if cadastral data has no civic number then we return cad_ncn as no accuracy comparison can ba made
    if not isinstance(p_list[1], str):
        return -1 # cadastral data no civic number

    # parcel (cadastral) and address point address part values in simple vars
    adp_civic = int(a_list[1])
    cad_min = int(p_list[1])
    cad_max = int(p_list[2])
    adp_sname = a_list[2] 
    cad_sname = p_list[3]
    # adp_stype = a_list[-1]
    # cad_stype = p_list[-1]

    # Setup flag vars as false
    flag_count = 0

    if (adp_civic >= cad_min) and (adp_civic <= cad_max):
        flag_count += 1
    if adp_sname == cad_sname:
        flag_count += 1

    if flag_count > 0:
        return 1
    if flag_count == 0:
        return 0

    print(parcel_row)
    print(address_row)
    sys.exit()


# --------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

output_path = os.getcwd()
match_gpkg = os.getenv('MATCHED_OUTPUT_GPKG')
match_lyr_nme = os.getenv('MATCHED_OUTPUT_LYR_NME')

project_gpkg = Path(os.getenv('DATA_GPKG'))
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')
addresses_lyr_nme = os.getenv('FLAGGED_AP_LYR_NME')
parcel_lyr_nme = 'parcels_cleaned'

mun_civic_gpkg = Path(os.getenv('QA_GPKG'))
mun_civic_lyr_nme = os.getenv('ST_MUN_CIVICS')

proj_crs = os.getenv('PROJ_CRS')

out_gpkg = Path(os.getenv('QA_GPKG'))
out_name = os.getenv('FLAGGED_ADP_LYR_NME')
# ----------------------------------------------------------------
# Logic

print('Loading in data')
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs)
mun_civics = gpd.read_file(mun_civic_gpkg, layer=mun_civic_lyr_nme, crs=proj_crs, driver='GPKG')
parcels = gpd.read_file(project_gpkg, layer=parcel_lyr_nme, crs=proj_crs)

print('Creating municipal civics flag')
addresses['mun_civic_flag'] = addresses[['link_field', 'number', 'street', 'stype_abbr']].apply(lambda row: civics_flag_builder(row[1],row[2],row[3],mun_civics[mun_civics['link_field'] == row[0]]), axis=1) 

print('Creating parcel location field flags')
addresses['parcel_loc_flag'] = addresses[['link_field', 'number', 'street', 'stype_abbr']].apply(lambda row: parcel_location_flag_builder(row, parcels[parcels['link_field'] == row[0]][['link_field', 'address_min', 'address_max', 'street_name', 'street_type']]), axis=1)

print(addresses[['link_field', 'number', 'street', 'stype_abbr', 'mun_civic_flag', 'parcel_loc_flag', 'geometry']].head())
# PCODE setup move to alternate file later
# PCODE_directoy = r'C:\projects\point_in_polygon\data\NB_data\PCODE\csv'

# for f in os.listdir(PCODE_directoy):
#     df = pd.read_csv(os.path.join(PCODE_directoy, f), encoding='latin1')
#     df.to_excel(os.path.join(r'C:\projects\point_in_polygon\data\NB_data\PCODE\excel', f.split('.')[0]+'.xlsx'))
#     # print(f)
#     # print(df['cpc_stname'].head())
#     # print(len(df.columns.tolist()))




# addresses[['link_field', 'number', 'street', 'stype_abbr', 'mun_civic_flag', 'geometry']].to_file(out_gpkg, layer=out_name, driver='GPKG')

print('DONE!')
