import os, sys
import pandas as pd
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
    inter = tuple(map(lambda p: bf.within(p), parcel_gdf['geometry']))
    inter = [x for x in inter if x == True]
    print(inter)
    sys.exit()
    true_count = sum(inter) # Because True = 1 False = 0
    return true_count


# -------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'environments.env'))
bf_gpkg = Path(os.getenv('NT_FINAL_OUTPUT'))
bf_lyr_nme = 'footprint_linkages'

pr_gpkg =  Path(os.getenv('NT_GPKG'))
ad_lyr_nme = os.getenv('CLEANED_AP_LYR_NAME')
parcel_lyr_nme = os.getenv('CLEANED_SP_LYR_NAME')

# -------------------------------------------------------
# Logic

print('Loading in layers')

addresses = gpd.read_file(pr_gpkg, layer=ad_lyr_nme, driver='GPKG')
footprints = gpd.read_file(bf_gpkg, layer=bf_lyr_nme, driver='GPKG')
parcels = gpd.read_file(pr_gpkg, layer=parcel_lyr_nme,  driver='GPKG')
print('Running check on intersect counts'//////////////////////////////54)
linked = footprints[footprints['method'] == 'data_linking']
linked['intersect_count'] = linked['geometry'].apply(lambda row: intersect_type_check(row, parcels))
#footprints['multi_intersect_flag'] = 
print(linked.head())
print('DONE!')
