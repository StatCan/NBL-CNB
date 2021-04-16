from shapely import geometry
from shapely.geometry import Point, Polygon, MultiPolygon
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import re

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

output_path = r'H:\point_to_polygon_PoC\data\workingfiles'

# Layer inputs
project_gpkg = "H:/point_to_polygon_PoC/data/data.gpkg"
addresses_lyr_nme = "yk_Address_Points"
bf_lyr_nme = "yk_buildings_sj"

# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
addresses = gpd.read_file(project_gpkg, layer= addresses_lyr_nme)
footprint = gpd.read_file(project_gpkg, layer= bf_lyr_nme)
  

print('Cleaning address points')
addresses = addresses[(addresses.CIVIC_ADDRESS != "RITE OF WAY")]
addresses = reproject(addresses, 26911)

print('Cleaning building footprints')
# Remove blanks and nulls
# footprint = footprint[(footprint.Join_Count > 0) & (footprint.STREET_NAME.notnull()) & (footprint.STREET_NAME != ' ')] # This causes missing intersects 224 cases should be triages into the nonlinking instead
footprint = explode(footprint) # Remove multipart polygons convert to single polygons
footprint['area'] = footprint['geometry'].area
footprint = footprint.loc[footprint.area >= 20.0] # Remove all buildings with an area of less than 20m**2
footprint = reproject(footprint, 26911)
print('Exporting cleaned datasets')

footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')

print('DONE!')
