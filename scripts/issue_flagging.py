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

Examples of potentially problematic situations include (examples with ✓ are those that have been added rest are planned):

Footprints:
- Footprint intersects with multiple parcels ✓
- Footprint contains many points with many unique addresses
- Footprint not within a parcel ✓
- Multiple footprints within one parcel

Points:
- Point not within parcel ✓
- Point address does not match parcel address (?)
- Multipoint within one parcel ✓
- More points than buildings in a parcel ✓

'''

# -------------------------------------------------------
# Functions


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

metrics_out_path = Path(os.getenv('METRICS_CSV_OUT_PATH'))

# -------------------------------------------------------
# Logic

print('Loading in layers')

starttime = datetime.datetime.now()
print(f'Start Time {starttime}')

if type(aoi_mask) != None:
    aoi_gdf = gpd.read_file(aoi_mask)

addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf) 
footprints = gpd.read_file(bf_path, mask=aoi_gdf)
parcels = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=aoi_gdf)

footprints.to_crs(crs=proj_crs, inplace=True)
parcels.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs=proj_crs, inplace=True)

metrics = []

parcels_drop_cols = parcels.columns.tolist()

# Linking fields creation
addresses["addresses_index"] = addresses.index
footprints["footprint_index"] = footprints.index
parcels['parcel_linkage'] = parcels.index

parcels_drop_cols.remove('geometry')
parcels_drop_cols.remove('Pan_Int')
parcels.drop(columns=parcels_drop_cols, inplace=True)

# Address Point Metrics

# Count of points not in parcels
addresses = gpd.sjoin(addresses, parcels, op='within', how='left')
ap_par_len = addresses['parcel_linkage'].isna().sum()

ap_n_pa = addresses.index[addresses['parcel_linkage'].isna()].tolist() # Put all the indexes into a list for later
print(f"METRIC: POINTS NOT IN PARCEL = {ap_par_len}")
metrics.append(['POINTS NOT IN PARCEL', ap_par_len])

# Counts of all parcels with more than 1 point
linkage_counts = addresses['parcel_linkage'].value_counts()
linkage_counts = linkage_counts[linkage_counts > 1].index.tolist() # save the indexes for later
linkage_len = len(linkage_counts)

print(f"METRIC: MORE THAN 1 POINT IN PARCEL = {linkage_len}")
metrics.append(['MORE THAN 1 POINT IN PARCEL', linkage_len])

# Footprint Metrics

# Get a count of all fooprints not in a parcel
spatial_join = gpd.sjoin(footprints[['footprint_index', 'geometry']], parcels[['parcel_linkage', 'geometry']], how='left')
sjoin_counts = spatial_join.footprint_index.value_counts()
footprints = footprints.merge(sjoin_counts, left_on='footprint_index', right_index=True, how='left')

footprints.rename(columns={'footprint_index_y': 'parcel_count', 'footprint_index_x': 'footprint_index'}, inplace=True)

no_intersect = footprints.index[footprints['parcel_count'].isna()].tolist()
print(f"METRIC: FOOTPRINT NOT IN A PARCEL = {len(no_intersect)}")
metrics.append(['FOOTPRINT NOT IN A PARCEL', len(no_intersect)])

# Multi Buildings in a singular parcel
multi_parcel_int_count = len(footprints.loc[footprints['parcel_count'] > 1])

print(f"METRIC: MULTI-INTERSECT FOOTPRINTS TO PARCELS =  {multi_parcel_int_count}")
metrics.append(['MULTI-INTERSECT FOOTPRINTS TO PARCELS', multi_parcel_int_count])

parcels.set_index('Pan_Int', inplace= True)

# Parcel Metrics
# Join points and footprints to the parcels for counts
parcel_join_ap = gpd.sjoin(parcels[['parcel_linkage', 'geometry']], addresses[['addresses_index', 'geometry']])
parcel_join_bf = gpd.sjoin(parcels[['parcel_linkage', 'geometry']], footprints[['footprint_index', 'geometry']])

p_ap_inter_cnt = parcel_join_ap.index.value_counts()
p_ap_inter_cnt.rename('ap_count', inplace=True)

p_bf_inter_cnt = parcel_join_bf.index.value_counts()
p_bf_inter_cnt.rename('bf_count', inplace=True)

parcels = parcels.merge(p_ap_inter_cnt, left_index= True, right_index=True, how='left')
parcels = parcels.merge(p_bf_inter_cnt, left_index= True, right_index=True, how='left')

print(parcels.head())

print(parcels[parcels['bf_count'] < parcels['ap_count']].head())
m_ap_than_bf_cnt = len(parcels[parcels['bf_count'] < parcels['ap_count']])
print(f"METRIC: MORE AP THAN BF IN PARCEL = {m_ap_than_bf_cnt}")
metrics.append(['MORE AP THAN BF IN PARCEL', m_ap_than_bf_cnt])

parcels[parcels['bf_count'] < parcels['ap_count']].to_file(output_gpkg, layer='parcel_test', driver='GPKG')

multi_bf_parcels = len(parcels[parcels['bf_count'] > 1])
print(f"METRIC: MULTI FOOTPRINTS IN PARCEL = {multi_bf_parcels}")
metrics.append(['MULTI FOOTPRINTS IN PARCEL', multi_bf_parcels])

multi_ap_parcels = len(parcels[parcels['ap_count'] > 1])
print(f"METRIC: MULTI ADDRESS POINTS IN PARCEL = {multi_ap_parcels}")
metrics.append(['MULTI ADDRESS POINTS IN PARCEL', multi_ap_parcels])

print('Creating and exporting metrics doc as spreadsheet')
metrics_df = pd.DataFrame(metrics, columns=['Metric', 'Count'])
metrics_df.to_csv(os.path.join(metrics_out_path, 'Data_Metrics.csv'), index=False)

# hour : minute : second : microsecond
print(f'Total Runtime: {datetime.datetime.now() - starttime}')

print('DONE!')
