import os, sys
import pandas as pd
import numpy as np
import geopandas as gpd
from dotenv import load_dotenv
from pathlib import Path

'''
The purpose of this script is to highlight potentially problematic building footprints as they relate to associated parcel fabrics and building points.

Examples of potentially problematic situations include:

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
        return np.Nan
    if intersect_count > 1:
        return 1

# -------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'environments.env'))
bf_gpkg = Path(os.getenv('NT_FINAL_OUTPUT'))
bf_lyr_nme = 'footprint_linkages'

pr_gpkg =  Path(os.getenv('NT_GPKG'))
ad_lyr_nme = os.getenv('CLEANED_AP_LYR_NAME')
parcel_lyr_nme = os.getenv('CLEANED_SP_LYR_NAME')

proj_crs = int(os.getenv('NT_PROJ_CRS'))

# -------------------------------------------------------
# Logic

print('Loading in layers')

addresses = gpd.read_file(pr_gpkg, layer=ad_lyr_nme, driver='GPKG')
footprints = gpd.read_file(bf_gpkg, layer=bf_lyr_nme, driver='GPKG')
parcels = gpd.read_file(pr_gpkg, layer=parcel_lyr_nme,  driver='GPKG')

footprints.to_crs(crs=proj_crs, inplace=True)
parcels.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs=proj_crs, inplace=True)

print('Running check on intersect counts')

footprints['intersect_count'] = footprints['geometry'].apply(lambda row: intersect_type_check(row, parcels))
footprints['multi_intersect_flag'] = footprints['intersect_count'] .apply(lambda row: intersect_type_check(*row))

print(footprints.head())
print('DONE!')
