import os
import matplotlib.pyplot as plt
import re
import string
import sys
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
from numpy.core.numeric import True_
from operator import add, index, itemgetter
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import pandas as pd
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo, LineString
from dotenv import load_dotenv
import datetime

'''
This script is responsible for all automated QA/QC steps and the production of certain layers that aid in manual qa/qc.

Currently this script produces:

    - line_link: A layer that visualizes the matches made in matching_master.py and creates a line from the original point to each match for that point (if any)
    - more to be added as needed 
'''


# ---------------------------------------------------------------------------------------------------
# Functions

def point_line_maker(matched_geometry, orig_geometry):
    '''
    Creates lines for illustrating the matches made during matching_master.py takes the matched point geometry and the original point geometry and returns a line 
    with those as the start and end points. 
    '''
    line_obj = LineString([orig_geometry, matched_geometry])
    return line_obj

# ---------------------------------------------------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

output_path = os.getcwd()

proj_crs = int(os.getenv('PROJ_CRS'))

matched_points_path = Path(os.getenv('MATCHED_OUTPUT_GPKG'))
matched_points_lyr_nme = 'point_linkages'

# matched_points_path = r'C:\projects\point_in_polygon\data\NB_data\parcelflag_filter.gpkg'
# matched_points_lyr_nme = 'linkage_filter_test'

project_gpkg = Path(os.getenv('DATA_GPKG'))
addresses_lyr_nme = os.getenv('FLAGGED_AP_LYR_NME')

qa_qc_gpkg = Path(os.getenv('QA_GPKG'))
# qa_qc_gpkg = r'C:\projects\point_in_polygon\data\NB_data\parcelflag_filter.gpkg'
# ----------------------------------------------------------------------------------------------------
# logic


match_adp = gpd.read_file(matched_points_path, layer=matched_points_lyr_nme, crs=proj_crs)
clean_adp = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs)

match_adp['line_geom'] = match_adp[['a_id', 'geometry']].apply(lambda row: point_line_maker(row[1], clean_adp[clean_adp['a_id'] == row[0]]['geometry'].tolist()[0]), axis=1)

match_adp = match_adp.set_geometry('line_geom')

match_adp.rename(columns={'geometry': 'point_geometry'}, inplace=True)
match_adp.rename(columns={'line_geom':'geometry'}, inplace=True)
match_adp= match_adp.set_geometry('geometry')

# Filter out those links that exceed the maximum limit for linkage distance
match_adp['link_length'] = match_adp['geometry'].apply(lambda l: l.length)

# Output line file to the qa_qc gpkg
line_links = match_adp.copy(deep=True)
line_links.drop(columns=['point_geometry'], inplace=True)
line_links.to_file(qa_qc_gpkg, layer=f"line_link_{datetime.datetime.now().strftime('%d_%m_%Y')}", driver='GPKG')

match_adp.drop(columns=['geometry'], inplace=True)
match_adp.rename(columns={'point_geometry':'geometry'}, inplace=True)
match_adp= match_adp.set_geometry('geometry')

match_adp.to_file(qa_qc_gpkg, layer='qc_points', driver='GPKG')

print('DONE!')
