import os
import re
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from dotenv import load_dotenv
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
# ------------------------------------------------------------------------------------------------
# Inputs
load_dotenv(os.path.join(os.getcwd(), 'environments.env'))

# Layer inputs
proj_crs = os.getenv('NT_CRS')

footprint_lyr = Path(os.getenv('NT_BF_PATH'))

ap_path = Path(os.getenv('NT_ADDRESS_PATH'))
# ap_lyr_nme = os.getenv('BC_ADDRESS_LYR_NME')
ap_add_fields = ['street_no', 'street', 'geometry']

linking_data_path = Path(os.getenv('NT_LINKING_PATH'))
# linking_lyr_nme = os.getenv('BC_LINKING_LYR_NME')
linking_ignore_columns = os.getenv('NT_LINKING_IGNORE_COLS') 

# AOI mask if necessary
aoi_mask = os.getenv('NT_ODB_MASK')

# output gpkg
project_gpkg = Path(os.getenv('NT_GPKG'))

# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
# if type(aoi_mask) != None:
#     aoi_gdf = gpd.read_file(aoi_mask)

# aoi_gdf = aoi_gdf.loc[aoi_gdf['CSD_UID'] == '5915022']

print('loading in linking data')
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

print('Cleaning address points')

addresses = addresses[ap_add_fields]
addresses = reproject(addresses, proj_crs)
addresses = gpd.sjoin(addresses, linking_data, op='within')
addresses.drop(columns=linking_cols_drop, inplace=True)
for f in ['index_right', 'index_left']:
    if f in addresses.columns.tolist():
        addresses.drop(columns=f, inplace=True)

print('Exporting cleaned dataset')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')
del addresses

print('Loading in footprint data')
footprint = gpd.read_file(footprint_lyr)# , mask=aoi_gdf)

print('Cleaning building footprints')
# footprint = explode(footprint) # Remove multipart polygons convert to single polygons
footprint['area'] = footprint['geometry'].area
footprint = footprint.loc[footprint.area >= 20.0] # Remove all buildings with an area of less than 20m**2
footprint = reproject(footprint, proj_crs)
footprint = gpd.sjoin(footprint, linking_data, how='left', op='within')
footprint.drop(columns=linking_cols_drop, inplace=True)

for f in ['index_right', 'index_left']:
    if f in footprint.columns.tolist():
        footprint.drop(columns=f, inplace=True)

print('Exporting cleaned dataset')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')

print('DONE!')
