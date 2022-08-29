
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import shapely
import sys
from pathlib import Path
from dotenv import load_dotenv
from bisect import bisect
from shapely import geometry
from shapely.geometry import Point, Polygon, MultiPolygon
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import datetime

from geovoronoi.plotting import subplot_for_map, plot_voronoi_polys_with_points_in_area
from geovoronoi import voronoi_regions_from_coords, points_to_coords
from shapely.ops import cascaded_union

'''
Test Applying Voroni polygons 

https://towardsdatascience.com/how-to-create-voronoi-regions-with-geospatial-data-in-python-adbb6c5f2134

'''

# ------------------------------------------------------------------------------------------------
# Functions



# ------------------------------------------------------------------------------------------------
# Inputs

load_dotenv(os.path.join(r'C:\projects\point_in_polygon\scripts', 'NB_environments.env'))
project_gpkg = Path(os.getenv('DATA_GPKG'))
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')
addresses_lyr_nme = os.getenv('FLAGGED_AP_LYR_NME')
aoi_mask = r'C:\projects\point_in_polygon\data\NB_data\voronoi_test_aoi.gpkg'
aoi_lyr_nme = 'voronoi_test_aoi'

proj_crs = int(os.getenv('PROJ_CRS'))

output_path = r'C:\projects\point_in_polygon\data\NB_data\voronoi_test.gpkg'

# ------------------------------------------------------------------------------------------------
# Logic

# Load in the data
bounds = gpd.read_file(aoi_mask, layer=aoi_lyr_nme)
addresses = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs, mask=bounds)
footprint = gpd.read_file(project_gpkg, layer=footprints_lyr_nme, crs=proj_crs, mask=bounds)

addresses.to_crs(crs= proj_crs, inplace=True)
footprint.to_crs(crs=proj_crs, inplace=True)
bounds.to_crs(crs=proj_crs, inplace=True)

footprint['centroid_geo'] = footprint['geometry'].apply(lambda bf: bf.centroid)
footprint.set_geometry('centroid_geo', inplace=True)

# Create the voronoi 
boundary_shape = cascaded_union(bounds.geometry)
coords = points_to_coords(footprint.centroid_geo)

poly_shapes, pts = voronoi_regions_from_coords(coords, boundary_shape)
voronoi = pd.DataFrame.from_dict(poly_shapes, orient='index')
# voronoi.rename({0:'geometry'}, inplace=True)
voronoi = gpd.GeoDataFrame(voronoi, geometry=0)
voronoi.to_file(aoi_mask, layer='test_voronoi')

print('DONE!')
