from shapely import geometry
from dotenv import load_dotenv
from pathlib import Path
from shapely.geometry import Point, Polygon, MultiPolygon
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import re
import sys
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
# ------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.getcwd(), 'environments.env'))

# Layer inputs
proj_crs = os.getenv('BC_CRS')

footprint_lyr = Path(os.getenv('BC_BF_PATH'))

ap_path = Path(os.getenv('BC_ADDRESS_PATH'))
# ap_lyr_nme = os.getenv('BC_ADDRESS_LYR_NME')

linking_gdb = Path(os.getenv('BC_LINKING_PATH'))
linking_lyr_nme = os.getenv('BC_LINKING_LYR_NME')
linking_ignore_columns = os.getenv('BC_LINKING_IGNORE_COLS') 

# AOI mask if necessary
aoi_mask = os.getenv('BC_ODB_MASK')

# output gpkg
project_gpkg = Path(os.getenv('OUTPUT_GPKG'))

# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
if len(aoi_mask) > 0 or type(aoi_mask) == None:
    aoi_gdf = gpd.read_file(aoi_mask)

print('Loading in address data')
addresses = gpd.read_file(ap_path, mask=aoi_gdf)
print('Loading in footprint data')
footprint = gpd.read_file(footprint_lyr, mask=aoi_gdf)
print('loading in linking data')
linking_data = gpd.read_file(linking_gdb, layer= linking_lyr_nme, linking_ignore_columns= linking_ignore_columns)
linking_data['link_field'] = range(1, len(linking_data.index)+1)
linking_data = reproject(linking_data, proj_crs, mask=aoi_gdf)

print('Cleaning address points')
# addresses = addresses[(addresses.CIVIC_ADDRESS != "RITE OF WAY")]
addresses = reproject(addresses, proj_crs)
addresses = gpd.sjoin(addresses, linking_data)
print('Cleaning building footprints')
# Remove blanks and nulls
# footprint = footprint[(footprint.Join_Count > 0) & (footprint.STREET_NAME.notnull()) & (footprint.STREET_NAME != ' ')] # This causes missing intersects 224 cases should be triages into the nonlinking instead
footprint = explode(footprint) # Remove multipart polygons convert to single polygons
footprint['area'] = footprint['geometry'].area
footprint = footprint.loc[footprint.area >= 20.0] # Remove all buildings with an area of less than 20m**2
footprint = reproject(footprint, proj_crs)
footprint = gpd.sjoin(footprint, linking_data)
footprint.drop(columns=['index_right'], inplace=True)

# print('Creating linking data field')
# footprint['link_field'] = footprint.apply(lambda x: '%s_%s_%s' % (x['LOT'], x['BLOCK'], x['PLAN_']), axis=1)
# addresses['link_field'] = addresses.apply(lambda x: '%s_%s_%s' % (x['LOT'], x['BLOCK'], x['PLAN_']), axis=1)

print('Exporting cleaned datasets')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')

print('DONE!')
