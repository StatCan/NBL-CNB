import geopandas as gpd
import numpy as np
import os
from numpy.core.numeric import NaN
import pandas as pd
import sys
from shapely.geometry import Point, Polygon, MultiPolygon
sys.path.insert(1, os.path.join(sys.path[0], ".."))

pd.options.mode.chained_assignment = None

'''
A side script to aid with the NWT point creation project. moves points to the footprint with the largest 
area on the parcel and adds certain parcel attributes to speed up matching process
'''

data_gdb = r'H:\point_to_polygon_PoC\data\nt_hybrid\data.gdb'
bf_lyr_nme = 'Building_Footprints'
sp_lyr_nme = 'Surveyed_Parcels'

condo_gdb = r'H:\point_to_polygon_PoC\data\nt_hybrid\condo.gdb'
condo_lyr_nme = 'Condominium_Units'

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

def find_largest_match(sp_index, polygon_data, join_key):
    '''Moves point to polygon with the largest area within the search parameters basic version works with most parcels special cases get their own functions'''
    polygon_data = polygon_data[polygon_data[join_key] == sp_index] # Filter in only those that match the parcel index
    if len(polygon_data) == 0:
        return np.nan
    top_area = polygon_data['area'].sort_values(ascending=False, ignore_index=True).tolist()[0]
    return polygon_data[polygon_data['area'] == top_area]['centroid_geo'].tolist()[0]
    
def condo_find_largest_match(cu_index, cu_centroid, cu_poly, polygon_data, join_key):
    '''Moves point to polygon with the largest area within the search parameters. Special case to deal with condo's and multi unit buildings where a unit level cadastral fabric is available'''
    
    def centroid_in_polygon(building_centroid, condo_polygons):
        '''Checks if the building centroid is contained in the condo polygon. returns a bool'''
        
        return condo_polygons.intersects(building_centroid)
    
    
    polygon_data = polygon_data[polygon_data[join_key] == cu_index] # Filter in only those that match the condo index  
    

    condo_poly = cu_poly
    condo_centroid = cu_centroid
    
    if len(polygon_data) == 0:
        return condo_centroid
    
    polygon_data.set_geometry('centroid_geo', inplace=True)
    polygon_data['centroid_intersect'] = polygon_data['centroid_geo'].apply(lambda bldg: centroid_in_polygon(bldg, condo_poly))
    true_polygons = polygon_data[polygon_data['centroid_intersect'] == True]
    
    if len(true_polygons) > 0: # If there are intersects then take the building with the largest area that is within the condo polygon and return the centroid
        top_area = true_polygons['area'].sort_values(ascending=False, ignore_index=True).tolist()[0]
        return true_polygons[true_polygons['area'] == top_area]['centroid_geo'].tolist()[0]
    
    # If there is no building centroid in the condo polygon then return the condo polygon centroid
    return condo_centroid

# --------------------------------------------------------------------------------------------------------------
print('Load in data and set crs')
bf_gdf = gpd.read_file(data_gdb, layer=bf_lyr_nme, driver="FileGDB")
sp_gdf = gpd.read_file(data_gdb, layer=sp_lyr_nme, driver="FileGDB")
cu_gdf = gpd.read_file(condo_gdb, layer=condo_lyr_nme, driver="FileGDB")

bf_gdf.to_crs(crs= proj_crs, inplace=True)
sp_gdf.to_crs(crs= proj_crs, inplace=True)
cu_gdf.to_crs(crs= proj_crs, inplace=True)

sp_gdf['sp_index'] = sp_gdf.index
cu_gdf['cu_index'] = cu_gdf.index
print('Prep data')

bf_gdf['area'] = bf_gdf['geometry'].area
bf_gdf = bf_gdf.loc[bf_gdf.area >= 20.0] # Remove all buildings with an area of less than 20m**2
bf_gdf = bf_gdf.reset_index()
bf_gdf.rename(columns={'index':'bf_index'}, inplace=True)
bf_gdf.set_index(bf_gdf['bf_index'])

# Projet everything into the geographic CRS
bf_gdf = reproject(bf_gdf, unproj_crs)
sp_gdf.to_crs(crs= unproj_crs, inplace=True)
cu_gdf.to_crs(crs=unproj_crs, inplace=True)

bf_gdf['centroid_geo'] = bf_gdf['geometry'].apply(lambda pt: pt.centroid)
bf_gdf = bf_gdf.set_geometry('centroid_geo')

# sjoin the cadastral data to the buildings
bf_gdf = gpd.sjoin(bf_gdf, sp_gdf[['sp_index', 'geometry']], how='left', op='within')
bf_gdf.drop(columns='index_right', inplace=True)
bf_gdf.rename(columns={'sp_index':'sp_joined_index'}, inplace=True)

bf_gdf = gpd.sjoin(bf_gdf, cu_gdf[['cu_index', 'geometry']], how='left', op='within')
bf_gdf.drop(columns='index_right', inplace=True)
bf_gdf.rename(columns={'cu_index':'cu_joined_index'}, inplace=True)

print('Configure Condos')
print(f'Condo data length: {len(cu_gdf)}')

cu_gdf.to_crs(crs=unproj_crs, inplace=True)

cu_gdf['cu_centroid'] = cu_gdf['geometry'].apply(lambda pt: pt.centroid) # get centroid geometry

cu_gdf['cu_new_geometry'] = cu_gdf[['cu_index','cu_centroid','geometry']].apply(lambda row: condo_find_largest_match(*row, polygon_data=bf_gdf[['sp_joined_index','cu_joined_index', 'area', 'centroid_geo', 'geometry']], join_key='cu_joined_index'), axis=1)

cu_gdf.dropna(subset=['cu_new_geometry'], inplace=True)

print(f'Moved Point Length: {len(cu_gdf)}')

# Test output delete when done
cu_gdf = cu_gdf.set_geometry('cu_new_geometry')
cu_gdf.dropna(subset=['cu_new_geometry'],  inplace=True)
cu_gdf.drop(columns=['geometry', 'cu_centroid'], inplace=True)
cu_gdf.to_file(r'H:\point_to_polygon_PoC\data\nt_hybrid\output_data.gpkg', layer='cu_moved_points', driver='GPKG')

cu_indexes = cu_gdf.cu_index.values.tolist()
matched_bfs = bf_gdf.loc[bf_gdf['cu_joined_index'].isin(cu_indexes)]['bf_index'].values.tolist()

bf_gdf = bf_gdf[~bf_gdf['bf_index'].isin(matched_bfs)] 

print('Finding Parcel Matches')

sp_gdf['new_geometry'] = sp_gdf['sp_index'].apply(lambda row: find_largest_match(row, bf_gdf[['sp_joined_index', 'area', 'centroid_geo']], 'sp_joined_index'))
sp_gdf.new_geometry.fillna(sp_gdf['geometry'], inplace=True)
# Post move column corrections
sp_gdf = sp_gdf.set_geometry('new_geometry')
sp_gdf.drop(columns='geometry', inplace=True)
sp_gdf.rename(columns={'new_geometry':'geometry'}, inplace=True)
sp_gdf = sp_gdf.set_geometry('geometry')

print('Output: ' + str(len(sp_gdf)))

sp_gdf.to_file(r'H:\point_to_polygon_PoC\data\nt_hybrid\output_data.gpkg', layer='moved_points', driver='GPKG')

print('DONE!')
