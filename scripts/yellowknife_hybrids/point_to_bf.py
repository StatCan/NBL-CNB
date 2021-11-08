
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import sys
from shapely.geometry import Point, Polygon, MultiPolygon
sys.path.insert(1, os.path.join(sys.path[0], ".."))

'''
A side script to aid withe the NWT point creation project. moves points to the footprint with the largest 
area on the parcel and adds certain parcel attributes to speed up matching process
'''

data_gdb = r'H:\point_to_polygon_PoC\data\nt_hybrid\data.gdb'
bf_lyr_nme = 'Building_Footprints'
sp_lyr_nme = 'Surveyed_Parcels'

unproj_crs = 4269
proj_crs = 26911

# --------------------------------------------------------------------------------------------------------------

def reproject(ingdf, output_crs):
    ''' Takes a gdf and tests to see if it is in the projects crs if it is not the funtions will reproject '''
    if ingdf.crs == None:
        ingdf.set_crs(epsg=output_crs, inplace=True)    
    elif ingdf.crs != f'epsg:{output_crs}':
        ingdf.to_crs(epsg=output_crs, inplace=True)
    return ingdf

def find_largest_match(sp_index, polygon_data):
    '''Moves point to polygon with the largest area within the search parameters'''
    polygon_data = polygon_data[polygon_data['joined_index'] == sp_index] # Filter in only those that match the parcel index
    if len(polygon_data) == 0:
        return np.nan
    top_area = polygon_data['area'].sort_values(ascending=False, ignore_index=True).tolist()[0]
    return polygon_data[polygon_data['area'] == top_area]['centroid_geo'].tolist()[0]
    

# --------------------------------------------------------------------------------------------------------------
print('Load in data and set crs')
bf_gdf = gpd.read_file(data_gdb, layer=bf_lyr_nme, driver="FileGDB")
sp_gdf = gpd.read_file(data_gdb, layer=sp_lyr_nme, driver="FileGDB")

bf_gdf.to_crs(crs= proj_crs, inplace=True)
sp_gdf.to_crs(crs= proj_crs, inplace=True)

sp_gdf['sp_index'] = sp_gdf.index

print('Prep footprint data')

bf_gdf['area'] = bf_gdf['geometry'].area
bf_gdf = bf_gdf.loc[bf_gdf.area >= 20.0] # Remove all buildings with an area of less than 20m**2
bf_gdf = bf_gdf.reset_index()
bf_gdf.rename(columns={'index':'bf_index'}, inplace=True)
bf_gdf.set_index(bf_gdf['bf_index'])

bf_gdf = reproject(bf_gdf, unproj_crs)
sp_gdf.to_crs(crs= unproj_crs, inplace=True)

bf_gdf['centroid_geo'] = bf_gdf['geometry'].apply(lambda pt: pt.centroid)
bf_gdf = bf_gdf.set_geometry('centroid_geo')

bf_gdf = gpd.sjoin(bf_gdf, sp_gdf, how='left', op='within')
bf_gdf.rename(columns={'sp_index':'joined_index'}, inplace=True)

print('Finding Matches')

sp_gdf['bf_centroid'] = sp_gdf['sp_index'].apply(lambda row: find_largest_match(row, bf_gdf[['joined_index', 'area', 'centroid_geo']]))

sp_gdf.dropna(axis=0, subset=['bf_centroid'])
# Post move column corrections
sp_gdf = sp_gdf.set_geometry('bf_centroid')
sp_gdf.drop(columns='geometry', inplace=True)
sp_gdf.rename(columns={'bf_centroid':'geometry'}, inplace=True)
sp_gdf = sp_gdf.set_geometry('geometry')

sp_gdf.to_file(r'H:\point_to_polygon_PoC\data\nt_hybrid\output_data.gpkg', layer='moved_points', driver='GPKG')

print('DONE!')
