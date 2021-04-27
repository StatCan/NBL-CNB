from shapely import geometry
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

output_path = r'H:\point_to_polygon_PoC\data\workingfiles'

# Layer inputs
footprint_gdb = r'H:\point_to_polygon_PoC\data\yk_buildings_gdb.gdb'
footprint_lyr_nme = 'yk_buildings'

ap_gdb = r'H:\point_to_polygon_PoC\data\yk_AddressPoints_gdb.gdb'
ap_lyr_nme = 'yk_Address_Points'

linking_gdb = r'H:\point_to_polygon_PoC\data\yk_parcels_gdb.gdb'
linking_lyr_nme = 'yk_parcels' 

# output gpkg
project_gpkg = "H:/point_to_polygon_PoC/data/data.gpkg"

# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
print('Loading in data')
addresses = gpd.read_file(ap_gdb, layer=ap_lyr_nme)
footprint = gpd.read_file(footprint_gdb, layer=footprint_lyr_nme)

linking_data = gpd.read_file(linking_gdb, layer= linking_lyr_nme, crs=26911)

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
footprint = gpd.sjoin(footprint, linking_data)
footprint.drop(columns=['index_right'], inplace=True)
print(footprint.head())
print('Creating linking data field')
footprint['link_field'] = footprint.apply(lambda x: '%s_%s_%s' % (x['LOT'], x['BLOCK'], x['PLAN_']), axis=1)
addresses['link_field'] = addresses.apply(lambda x: '%s_%s_%s' % (x['LOT'], x['BLOCK'], x['PLAN_']), axis=1)

print('Exporting cleaned datasets')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')

print('DONE!')
