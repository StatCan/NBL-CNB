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
Generates a report of counts based on known potentially problematic situations

Examples of potentially problematic situations include:

Footprints:
- Footprint intersects with multiple parcels
- Footprint contains many points with many unique addresses
- Footprint not within a parcel
- Multiple footprints within one parcel

Points:
- Point not within parcel ✓
- Point address does not match parcel address
- Multipoint within one parcel
- More points than buildings in a parcel


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

addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf) 
footprints = gpd.read_file(bf_path, mask=aoi_gdf)
parcels = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=aoi_gdf)

footprints.to_crs(crs=proj_crs, inplace=True)
parcels.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs=proj_crs, inplace=True)

metrics = []

# Linking fields creation
addresses["addresses_index"] = addresses.index
footprints["footprint_index"] = footprints.index
parcels['parcel_linkage'] = range(1, int(len(parcels.index)+1))

parcels_drop_cols = parcels.columns.tolist()
parcels_drop_cols.remove('geometry')

addresses = gpd.sjoin(addresses, parcels, op='within', how='left')

# Count of points not in parcels
print(f"METRIC: POINTS NOT IN PARCEL = {addresses['parcel_linkage'].isna().sum()}")
metrics.append(['POINTS NOT IN PARCEL', addresses['parcel_linkage'].isna().sum()])

# Counts of all parcels with more than 1 point
print(addresses['parcel_linkage'].value_counts().drop(labels=1, inplace= True))
sys.exit()
print(f"METRIC: MORE THAN 1 POINT IN PARCEL = {len(addresses['parcel_linkage'].value_counts().drop(labels=1, inplace= True))}")
metrics.append(['MORE THAN 1 POINT IN PARCEL', len(addresses['parcel_linkage'].value_counts().drop(labels=1, inplace= True))])

sys.exit()
# Intersect Count check
# print('Running check on intersect counts')
# footprints['intersect_count'] = footprints['geometry'].apply(lambda row: intersect_type_check(row, parcels))

# print('Counting Flags')
# footprints['multi_intersect_flag'] = footprints['intersect_count'].apply(lambda row: intersect_count_flag(row))

# footprints.to_file(output_gpkg, layer='record_flagging', driver='GPKG')

# hour : minute : second : microsecond
print(f'Total Runtime: {datetime.datetime.now() - starttime}')

print('DONE!')
