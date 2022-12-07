import geopandas as gpd
import numpy as np
import os
import pandas as pd
import sys
import shapely
from pathlib import Path
from shapely.geometry import MultiLineString, Polygon
from shapely.validation import make_valid
sys.path.insert(1, os.path.join(sys.path[0], ".."))

'''https://stackoverflow.com/questions/3623703/how-can-i-split-a-polygon-by-a-line

Inital flow:

- get all lines that a polygon intersects with
- then for each line in the linkage split the polygon along the lines
- create methods for exporting splits, slivers, other geometry subsets

'''


class PolygonCutter:
    
    '''Process for cutting polygons when they cross an intersect point'''
    def __init__(self, bld_poly: gpd.GeoDataFrame, cut_geom: gpd.GeoDataFrame, crs=4326) -> None:
        
        def ValidateGeometry(input_geometry) -> gpd.GeoSeries:
            '''Checks if input geometry is valid and if invalid attempts to make it valid accepts Geodataframes and Geoseries'''
            if type(input_geometry) == gpd.GeoSeries:
                input_geometry = input_geometry.apply(lambda geom: make_valid(geom))
            if type(input_geometry) == gpd.GeoDataFrame:
                input_geometry = input_geometry['geometry'].apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
            return input_geometry

        def check_geom(input_gdf: gpd.GeoDataFrame, geometry_column= 'geometry') -> gpd.GeoDataFrame:
            '''Checks to see if the input  geometry is a line. If polygon converts to lines. If points or other returns a geometry error'''
            input_gdf.reset_index(inplace=True)
            if input_gdf.geometry[0].geom_type in ['LineString', 'MultiLineString']:
                # If the geometry is already in line type then just strip attributes 
                return input_gdf
            
            # If inputs are polygons then convert them to lines and strip attributes
            if input_gdf.geometry[0].geom_type in ['Polygon', 'MultiPolygon']:
                
                # Ensure all geometry is valid
                input_gdf['geometry'] = input_gdf['geometry'].buffer(0)

                # Check if any multi-polgyons exists explode them
                # input_gdf['isMulti'] = input_gdf.apply(lambda row: True if row['geometry'].geom_type != 'Polygon' else False, axis=1)
                # multifeatures = input_gdf.loc[input_gdf['isMulti'] == True]
                # if len(multifeatures) > 0:
                    # input_gdf = input_gdf.explode(index_parts=True)
                # input_gdf.drop(columns=['isMulti'], inplace=True)
                # convert to lines
                input_gdf['geometry'] = input_gdf['geometry'].apply(lambda p: p.boundary)
                return input_gdf.explode(index_parts=True)

            # If the geometry is a point or mutipoint raise an error
            if input_gdf.geometry[0].geom_type in ['Point', 'MultiPoint']:
                raise IOError('Shape is not a Polygon or Line')

        def FindIntersects(input_geom: gpd.GeoDataFrame, search_geometry: gpd.GeoDataFrame, input_link_field: str, search_link_field: str) -> gpd.GeoDataFrame:
            '''finds all intersections between the input geometry and the search geometry'''

            joined_geom = gpd.sjoin(input_geom, search_geometry[[search_link_field, 'geometry']], op='intersects')
            input_geom['line_ints'] = input_geom[input_link_field].apply(lambda x: tuple(joined_geom[joined_geom[input_link_field] == x][search_link_field].tolist()))
            return input_geom

        def CutPolygons(poly, cut_geom):
            '''Cuts the input polygon by the lines linked to it during the FindIntersects Step
            Run the FindIntersects step before calling this function'''

        # Load in the inputs to geodataframes
        bp = bld_poly
        cut_geom = cut_geom
        # Ensure projection consistency
        bp.to_crs(crs=crs, inplace=True)
        cut_geom.to_crs(crs=crs, inplace=True)

        # Ensure all valid geometry
        bp['geometry'] = ValidateGeometry(bp)
        cut_geom['geometry'] = ValidateGeometry(cut_geom)

        # Calc unique values for data to link between datasets
        bp['bp_index'] = range(1, len(bp.index) + 1)
        cut_geom['cut_index'] = range(1, len(cut_geom.index) + 1)

        # convert the cut geometry to lines if necessary
        self.line_geom = check_geom(cut_geom)
        #self.line_geom.to_file(Path(os.getenv('OUT_GPKG')), layer='parcel_lines')

        bp = FindIntersects(bp, self.line_geom, 'bp_index', 'cut_index')
        cut_polys = CutPolygons(bp, cut_geom)
        sys.exit()
        # Dont use this method its really slow
        # self.clipped = gpd.clip(bp, cut_geom)
        # self.clipped = self.clipped['geometry'].explode()
        
        # Merge all the lines into one mega line wont work either shapely geometrytypeerror polygon not split by multistring

        # splits = bp.apply(lambda geom: shapely.ops.split(geom['geometry'], merged_lines), axis=1)
        # print(splits)
        # sys.exit()
        # # Gather all intersections per building
        # inp, res = bp.sindex.query_bulk(cut_geom.geometry, predicate='intersects')
        # bp['intersects'] = np.isin(np.arrange(0, len(cut_geom)),inp)
        # print(bp.head())
        

def main():
    # setup for testing purposes
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), 'cutting.env'))

    aoi_path = Path(os.getenv('AOI_EXTENT'))
    aoi_lyr_nme = os.getenv('AOI_LYR_NME')

    parcel_path = Path(os.getenv('PARCEL_PTH'))
    bld_path = Path(os.getenv('BLD_PTH'))
    bld_lyr_nme = os.getenv('BLD_LYR_NME')
    
    out_gpkg = Path(os.getenv('OUT_GPKG'))
    out_bld_lyr_nme = os.getenv('OUT_BLD_LYR_NME')
    out_pcl_lines_lyr_nme = os.getenv('OUT_PARCEL_LINES_LYR_NME')

    # Load in the data
    aoi_mask = gpd.read_file(aoi_path, layer=aoi_lyr_nme)

    bld_gdf = gpd.read_file(bld_path, layer=bld_lyr_nme, mask=aoi_mask)
    bld_gdf = bld_gdf[bld_gdf.geometry != None]
    
    cut_gdf = gpd.read_file(parcel_path, mask=aoi_mask)
    cut_gdf = cut_gdf[cut_gdf.geometry != None]

    print('cutting buildings')
    clipped_polys = PolygonCutter(bld_poly=bld_gdf, cut_geom=cut_gdf)
    clipped_polys.clipped.to_file(out_gpkg, layer=out_bld_lyr_nme)


if __name__ == '__main__':
    main()
    print('DONE!')
