import geopandas as gpd
import numpy as np
import os
import pandas as pd
import sys
import shapely
from pathlib import Path
from dotenv import load_dotenv
from operator import itemgetter
from shapely.geometry import MultiLineString, Polygon
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import datetime

'''https://stackoverflow.com/questions/3623703/how-can-i-split-a-polygon-by-a-line

Inital flow:

- get all lines that a polygon intersects with
- then for each line in the linkage split the polygon along the lines
- create methods for exporting splits, slivers, other geometry subsets

'''

class PolygonCutter():
    
    '''Process for cutting polygons when they cross an intersect point'''
    def __init__(self,bld_poly_path:str, cut_geom_path:str, bld_poly_lyr_nme=None, cut_geom_lyr_nme=None, crs=4326) -> None:
        
        def check_geom(input_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
            '''Checks to see if the input  geometry is a line. If polygon converts to lines. If points or other returns a geometry error'''
            
            if input_gdf.geometry[0].geom_type in ['LineString', 'MultiLineString']:
                # If the geometry is already in line type then just strip attributes 
                return input_gdf['geometry']
            
            # If inputs are polygons then convert them to lines and strip attributes
            if input_gdf.geometry[0].geom_type in ['Polygon', 'MultiPolygon']:
                
                # Ensure all geometry is valid
                input_gdf['geometry'] = input_gdf['geometry'].buffer(0)
                

                # Check if any multipolgyons exists explode them
                input_gdf['isMulti'] = input_gdf.apply(lambda row: True if row['geometry'].geom_type != 'Polygon' else False, axis=1)
                MultiFeatures = input_gdf.loc[input_gdf['isMulti'] == True]
                if len(MultiFeatures) > 0:
                    input_gdf = input_gdf.explode()
                input_gdf.drop(columns=['isMulti'], inplace=True)
                # convert to lines
                input_gdf = input_gdf['geometry'].apply(lambda p: p.boundary)
                return input_gdf.explode(index_parts=True)

            # If the geometry is a point or mutipoint raise an error
            if input_gdf.geometry[0].geom_type in ['Point', 'MultiPoint']:
                raise IOError('Shape is not a Polygon or Line')

        def find_intersects(input_geom, search_geometry) -> tuple:
            '''finds all intersections between the input geometry and the search geometry'''

            # First check if there are any at all

        # Load in the inputs to geodataframes 
        bp = gpd.read_file(bld_poly_path, layer=bld_poly_lyr_nme)
        cut_geom = gpd.read_file(cut_geom_path, layer=cut_geom_lyr_nme)
        
        # Ensure projection consistency
        bp.to_crs(crs=crs, inplace=True)
        cut_geom.to_crs(crs=crs, inplace=True)

        # convert the cut geometry to lines if necessary
        line_geom = check_geom(cut_geom)

        self.clipped = gpd.clip(bp, cut_geom)
        self.clipped = self.clipped['geometry'].explode()
        
        # sys.exit()
        # # convert all the lines into a single line and then cut the buildings from there
        # line_geom_list = line_geom.tolist()
        # merged_lines = MultiLineString(line_geom_list)
        # merged_lines = shapely.ops.linemerge(merged_lines)
        # merged_lines = shapely.ops.unary_union(merged_lines)
        
        # # Gather all intersections per building
        # inp, res = bp.sindex.query_bulk(cut_geom.geometry, predicate='intersects')
        # bp['intersects'] = np.isin(np.arrange(0, len(cut_geom)),inp)
        # print(bp.head())
        

def main():

    parcel_path = r'C:\projects\point_in_polygon\data\MB_data\Survey Parcel.shp'
    bld_path = r'C:\projects\point_in_polygon\data\MB_data\Winnipeg_2019.gdb'
    bld_lyr_nme = 'auto_building_2'
    
    out_path = r'C:\projects\point_in_polygon\data\MB_data'
    out_lyr_nme = 'clipped_buildings'
    
    print('cutting buildings')
    clipped_polys = PolygonCutter(bld_poly_path=bld_path, bld_poly_lyr_nme=bld_lyr_nme, cut_geom_path=parcel_path)
    clipped_polys.clipped.to_file(out_path, layer=out_lyr_nme)
if __name__ == '__main__':
    main()
    print('DONE!')
