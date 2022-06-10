import datetime
import os
import re
import string
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
from math import pi

'''This script takes the raw output from PCODE and joins it back with the coorespondence table so that it can be used as part of the matching process
PCODE results are for both the parcels (pan) and the geonb address points (gnb).'''

# ----------------------------------------------------------------------------
# Inputs

out_path = r'C:\projects\point_in_polygon\data\NB_data\PCODE\joined_files'

# Path to coorespondence csv files
pan_co = r'C:\projects\point_in_polygon\data\NB_data\PCODE\Pan_ncb.csv'
gnb_co = r'C:\projects\point_in_polygon\data\NB_data\PCODE\geonb_addresses_v2.csv'
co_link_field = 'TmpUID'

# PCODE output
PCODE_file_path = r'C:\projects\point_in_polygon\data\NB_data\PCODE\excel'
pan_PCODE_lyr_nme = 'PAN_Addmatch_hlgeo_204g_inventory.csv'
gnb_PCODE_lyr_nme = 'Addmatch_hlgeo_204g_inventory.xlsx'
PCODE_link_field = 'rec_id'

# -----------------------------------------------------------------------------
# Logic

print('Importing co tables')
pan_co_df = pd.read_csv(pan_co, encoding='latin1')
gnb_co_df = pd.read_csv(gnb_co, encoding='latin1')

# join pan co table to PCODE results importing on the key fields
print('Importing and joining pcode results for pan')
PCODE_import_fields = ['rec_id','official_munname', 'match_stname_key_no_art', 'match_sttype_key', 'match_stdir_key', 'street_number']
PCODE_pan_df = pd.read_csv(os.path.join(PCODE_file_path, pan_PCODE_lyr_nme), usecols=PCODE_import_fields, encoding='latin1')
pan_co_df = pan_co_df.merge(PCODE_pan_df, how='left', left_on=co_link_field, right_on=PCODE_link_field)
pan_co_df.to_csv(os.path.join(out_path, 'pan_co_joined.csv'), index=False)
print('Importing and joining PCODE results for gnb')
PCODE_gnb_df = pd.read_excel(os.path.join(PCODE_file_path, gnb_PCODE_lyr_nme), usecols=PCODE_import_fields)
gnb_co_df =gnb_co_df.merge(PCODE_gnb_df, how='left', left_on=co_link_field, right_on=PCODE_link_field)

print('Exporting joined files')
pan_co_df.to_csv(os.path.join(out_path, 'pan_PCODE_joined.csv'), index=False)
gnb_co_df.to_csv(os.path.join(out_path, 'gnb_PCODE_joined.csv'), index=False)

print('DONE!')
