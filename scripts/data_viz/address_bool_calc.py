import os, sys
import pandas as pd
import geopandas as gpd

# -------------------------------------------------------------------------------------
# Functions


def check_presence(row):
    score = row.sum()
    if score > 0:
        return 1
    else:
        return 0


# -------------------------------------------------------------------------------------
# Inputs

addressIO_path = r'Z:\working\open_addresses\ca'
csd_path = r'Z:\working\dashboard_work\CSD_NAR.gdb'
csd_lyr_nme = 'CSD_w_NAR'
out_path = r'Z:\working\dashboard_work'

# -------------------------------------------------------------------------------------
# Logic

# load in cd data

csd = gpd.read_file(csd_path, layer=csd_lyr_nme)
csd.to_crs(crs=4326, inplace=True)
# walk through all files in the addressIO directory and return all the geojsons
csd_list = []
for root, dirs, files in os.walk(addressIO_path):
    for file in files:
        if file.endswith('.geojson'):
            print(f'Reading in: {file}')
            working_gdf = gpd.read_file(os.path.join(root, file))
            working_gdf.to_crs(crs=4326, inplace=True)

            if working_gdf.geom_type[0] != 'Point':
                print(f'{file} is not address points. Skipped')
                continue

            working_gdf = gpd.sjoin(working_gdf, csd[['CSDUID', 'geometry']], op='within', how='left')
            csd_id = list(set(working_gdf['CSDUID'].tolist()))
            csd_list.append(csd_id)

# for every list in the list explode into one list
cds = [i for sl in csd_list for i in sl]

csd['add_io'] = csd['CSDUID'].isin(cds)

csd['nar'] = csd[['NAR_COUNT']].apply(lambda x: check_presence(x), axis=1)
csd['addresses'] = csd[['nar', 'add_io']].apply(lambda x: check_presence(x), axis=1)
csd.to_file(os.path.join(out_path, 'csd_addr_cnts.shp'))
print('DONE!')
