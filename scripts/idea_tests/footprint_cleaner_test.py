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
import pandas as pd
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo
from dotenv import load_dotenv
import datetime

'''Test to see if it is possible to recreate Alex's cleaning methodology in python. There are 3 goals to the methodology:

1.) Remove as many sheds from the address linking as possible as they are considered unaddressable
2.) Remove as many overlaps as possible to eliminate false positives
3.) Cut buildings that legitimately span multiple parcels so that matches for things like units (or townhomes, etc) are more accurate

'''

# ------------------------------------------------------------------------------------------------
# Functions

def reproject(ingdf, output_crs):
    ''' Takes a gdf and tests to see if it is in the projects crs if it is not the funtions will reproject '''
    if ingdf.crs == None:
        ingdf.set_crs(epsg=output_crs, inplace=True)    
    elif ingdf.crs != f'epsg:{output_crs}':
        ingdf.to_crs(epsg=output_crs, inplace=True)
    return ingdf


# ------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

geo_crs = os.getenv('CRS')
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
aoi_mask = Path(os.getenv('AOI_MASK'))

# output gpkg
project_gpkg = Path(os.getenv('DATA_GPKG'))
rd_crs = os.getenv('RD_CRS')

# for testing only
test_gpkg = r'C:\projects\point_in_polygon\data\NB_data\clean_test.gpkg'

# ------------------------------------------------------------------------------------------------
# Logic

# Load in layers
if type(aoi_mask) != None:
    aoi_gdf = gpd.read_file(aoi_mask)

linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme, linking_ignore_columns=linking_ignore_columns, mask=aoi_gdf)
footprint = gpd.read_file(footprint_lyr, layer=footprint_lyr_name ,mask=aoi_gdf)

linking_data = reproject(linking_data, proj_crs)
# addresses.to_crs(crs= proj_crs, inplace=True)
footprint = reproject(footprint, proj_crs)
footprint['geometry'] = footprint['geometry'].buffer(0)

# NEW STUFF STARTS HERE

# # Convert parcel polygons to lines
# linking_data['geometry'] = linking_data['geometry'].boundary # .exterior if that returns an odd result

# # Create 1m buffer and then clip the buildings by that buffer
# linking_data['buffer_geom'] = linking_data['geometry'].geometry.buffer(0.5)
# linking_data.set_geometry('buffer_geom', inplace=True)
# footprint['AREA_1'] = footprint['geometry'].area
# footprint = gpd.overlay(footprint, linking_data, how='difference')
# footprint = footprint.explode('geometry', index_parts=True)
# footprint['AREA_2'] = footprint['geometry'].area
# footprint = footprint.query("((AREA_2/AREA_1)*100) > 10") # if split polygon is less than x percent of original polygon remove as a sliver

# Remove the 'sheds'

print(footprint.columns)


print('DONE')
