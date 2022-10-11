import os, sys
import collections
import math
import fiona
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape

# --------------------------------------------------------------------------------------------------------------------
# Functions


def explode_list_of_lists(list_of_lists):
    '''Explode a list of lists into a 1d list of only unique values'''
    return tuple(set([i for sl in list_of_lists for i in sl]))


def load_valid_geometry(layer_path, layer_name=None):
    '''
    Loads in only those records that contain valid geometry.
    Removes records with invalid geometry
    '''

    # Read data
    collection = list(fiona.open(layer_path, 'r'))
    df1 = pd.DataFrame(collection)

    # Check Geometry
    def isvalid(geom):
        try:
            shape(geom)
            return 1
        except:
            return 0

    df1['isvalid'] = df1['geometry'].apply(lambda x: isvalid(x))
    df1 = df1[df1['isvalid'] == 1]
    collection = json.loads(df1.to_json(orient='records'))

    # Convert to geodataframe
    gdf = gpd.GeoDataFrame.from_features(collection)
    return gdf


def get_coverage(source):
    csd_list = []
    print(f'Getting counts for : {os.path.split(source)[-1]}')
    for root, dirs, files in os.walk(p):
        for file in files:
            if file.endswith('.geojson') or file.endswith('.shp'):
                print(f'Reading in: {file}')
                working_gdf = gpd.read_file(os.path.join(root, file))
                working_gdf.to_crs(crs=4326, inplace=True)
                if not 'CSDUID' in working_gdf.columns.tolist():
                    working_gdf = gpd.sjoin(working_gdf, csd[['CSDUID', 'geometry']], op='within', how='left')
                csd_id = tuple(set(working_gdf['CSDUID'].tolist()))
                csd_list.append(csd_id)

        for d in dirs:
            if d.endswith('.gdb'):
                d_path = os.path.join(root, d)
                layers = fiona.listlayers(d_path)
                for lyr in layers:
                    print(f'Reading in layers from: {d}')
                    working_gdf = load_valid_geometry(os.path.join(root, d_path), layer_name=lyr)
                    # working_gdf = gpd.read_file(os.path.join(root, d_path), layer=l)
                    working_gdf.set_crs(crs=4326, inplace=True)
                    working_gdf = gpd.sjoin(working_gdf, csd[['CSDUID', 'geometry']], op='within', how='left')
                    csd_id = tuple(set(working_gdf['CSDUID'].tolist()))
                    csd_list.append(csd_id)
    return csd_list

def check_presence(row):
    score = row.sum()
    if score > 0:
        return 1
    else:
        return 0

# --------------------------------------------------------------------------------------------------------------------
# Inputs

bld_src_paths = [ r'Z:\working\nrcan_buildings', r'Z:\working\ODB_buildings', r'Z:\working\bing_buildings']
# bld_src_paths = [r'Z:\working\ODB_buildings']
out_path = r'Z:\working\dashboard_work'
csd_path = os.path.join(out_path, 'csd_w_addr.shp')

# --------------------------------------------------------------------------------------------------------------------
# Logic

csd = gpd.read_file(csd_path)

# Get a list of all CSDIDs that contain data from the source directories.
# Also sort by source to get coverage by source
csd_dict = collections.defaultdict(list)

for p in bld_src_paths:
    csd_dict[os.path.split(p)[-1]] = get_coverage(p)

# Add a new field to the CSD's and add in the
# for every list in the list explode into one list
key_list = []
for key in tuple(csd_dict.keys()):
    # explode and calculate var per source
    exploded = explode_list_of_lists(csd_dict[key])
    while type(exploded[0]) == tuple:
        exploded = explode_list_of_lists(exploded)
    csd[key] = csd['CSDUID'].isin(exploded)
    key_list.append(key)

csd['buildings'] = csd[key_list].apply(lambda x: check_presence(x), axis=1)
csd.to_file(os.path.join(out_path, 'csd_w_adbl.shp'))
print('DONE!')
