import os
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from numpy.core.numeric import True_
import pandas as pd
from dotenv import load_dotenv
from pandas.core.indexes import multi
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon


# ----------------------------------------------------------
# Functions

def measure_road_dist(poly, road_name, roads):
    ''' Returns the distance to the closest road segment that matches the name of civic address in the address point'''

    road = roads[roads['L_STNAME_C']==road_name]
    

# ----------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'environments.env'))

pr_gpkg = Path(os.getenv('NT_FINAL_OUTPUT'))
matched_bf_lyr_nme = 'footprint_linkages'

rd_gpkg = Path(os.getenv('NT_RD_GPKG'))
rd_lyr_nme = os.getenv('NRN_NT_12_0_ROADSEG')
rd_add_tbl_nme = os.getenv('NT_RD_TBL_NME')

proj_gpkg = os.getenv('NT_GPKG')
ad_lyr_nme =  os.getenv('CLEANED_AP_LYR_NAME')

prj_crs = int(os.getenv('NT_PROJ_CRS'))

# ---------------------------------------------------------
# Logic

print('Step 1. Load in Data')

roads = gpd.read_file(rd_gpkg, layer=rd_lyr_nme)
addresses = gpd.read_file(proj_gpkg, layer=ad_lyr_nme)
footprints = gpd.read_file(pr_gpkg, layer=matched_bf_lyr_nme)

# Set the crs to all match
roads.to_crs(prj_crs, inplace=True)
addresses.to_crs(prj_crs, inplace=True)
footprints.to_crs(prj_crs, inplace=True)

print('Step 2. Apply buisness rules to linked data')

multi_links = footprints.groupby('addresses_index')['addresses_index'].count() # get all counts of adresses_index values
multi_links = multi_links[multi_links > 1] # Keep only values with more than 1 link as we only want to look at that links with more than 1

multi_df = footprints[footprints['addresses_index'].isin(multi_links.index.tolist())]
# multi_df['dist_to_road'] = footprints[]

print('DONE!')
