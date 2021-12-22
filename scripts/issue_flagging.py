import os, sys
import pandas as pd
import numpy as np
import geopandas as gpd
from dotenv import load_dotenv
from pathlib import Path
import shapely.speedups
import datetime

shapely.speedups.enable()

'''
The purpose of this script is to highlight potentially problematic building footprints as they relate to associated parcel fabrics and building points.

Examples of potentially problematic situations include:0

-Footprint intersects with multiple parcels
-Footprint contains many points with many unique addresses

'''

# -------------------------------------------------------
# Functions

def intersect_type_check(bf, parcel_gdf):
    '''
    Function to check for type of intersection between building footprints and linking data. Outputs an integer value based on the number of intersections
    '''

    inter = tuple(map(lambda p: p.intersects(bf), parcel_gdf['geometry']))
    
    true_count = sum(inter) # Because True == 1 False == 0    
    return true_count

def intersect_count_flag(intersect_count):
    '''Returns a flag when more than 1 intersect is detected'''
    if intersect_count <= 1:
        return np.nan
    if intersect_count > 1:
        return 1

# -------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))
bf_path = Path(os.getenv('BF_PATH'))
# bf_lyr_nme = 'footprint_linkages'

ap_path = Path(os.getenv('ADDRESS_PATH'))
ap_lyr_nme = os.getenv('ADDRESS_LAYER')

linking_data_path = Path(os.getenv('LINKING_PATH'))
linking_lyr_nme = os.getenv('LINKING_LYR_NME')

output_gpkg = Path(os.getenv('OUTPUT_GPKG'))

proj_crs = int(os.getenv('PROJ_CRS'))

aoi_mask = Path(os.getenv('AOI_MASK'))

# -------------------------------------------------------
# Logic

print('Loading in layers')

starttime = datetime.datetime.now()

if type(aoi_mask) != None:
    aoi_gdf = gpd.read_file(aoi_mask)

# addresses = pd.read_csv(ap_path)
# addresses = gpd.GeoDataFrame(addresses, geometry=gpd.points_from_xy(addresses.longitude, addresses.latitude))

footprints = gpd.read_file(bf_path, mask=aoi_gdf)
parcels = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=aoi_gdf)

footprints.to_crs(crs=proj_crs, inplace=True)
parcels.to_crs(crs=proj_crs, inplace=True)
# addresses.to_crs(crs=proj_crs, inplace=True)

print('Running check on intersect counts')
footprints['intersect_count'] = footprints['geometry'].apply(lambda row: intersect_type_check(row, parcels))

print('Counting Flags')
footprints['multi_intersect_flag'] = footprints['intersect_count'] .apply(lambda row: intersect_count_flag(row))

footprints.to_file(output_gpkg, layer='record_flagging', driver='GPKG')

# hour : minute : second : microsecond
print(f'Total Runtime: {datetime.datetime.now() - starttime}')

print('DONE!')
