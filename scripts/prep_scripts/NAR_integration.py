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

# -----------------------------------------------------------------
# Inputs

base_path = r'C:\projects\point_in_polygon\data\NB_data'
address_txt_nme = 'geonb_and_addresses_corruptions_removed.txt'
link_csv_nme = 'nbl_with_sbgr_nar_links_pr13.csv'

# -----------------------------------------------------------------
# Logic

links = pd.read_csv(os.path.join(base_path, link_csv_nme))
address = pd.read_csv(os.path.join(base_path, address_txt_nme))

merged = address.merge(links, right_on='nbl_objectid', left_on='OBJECTID')

merged_gdf = gpd.GeoDataFrame(merged, geometry=gpd.points_from_xy(merged.LONGITUDE, merged.LATITUDE))

merged_gdf.to_file(os.path.join(base_path, 'gnb_nar_linked.gpkg'), layer='gnb_nar_linked', driver='GPKG')

print('DONE!')
