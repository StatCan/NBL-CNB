import os, sys
import collections
import fiona
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
 

# ----------------------------------------------------------------------------------------------------------------------

# Functions 

def explode_list_of_lists(list_of_lists):
    '''Explode a list of lists into a 1d list of only unique values'''
    return tuple(set([i for sl in list_of_lists for i in sl]))

def get_coverage(source, geometry_layer, key_field='CSDUID', geo_field='geometry', proj_crs=4326): 
    '''Get the unique ID for all pieces of geometry that each layer in the source directory intersects with. Returns a
    list of all the unique ID's'''

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
        gdf.set_crs(proj_crs, inplace=True)
        return gdf

    csd_list = []
    print(f'Getting counts for : {os.path.split(source)[-1]}')
    for root, dirs, files in os.walk(p):
        for file in files:
            if file.endswith('.geojson') or file.endswith('.shp'):
                if 'parcels' not in file:
                    print(f'{file} is not a parcels file. Skipping')
                    continue

                print(f'Reading in: {file}')
                working_gdf = gpd.read_file(os.path.join(root, file))
                working_gdf.to_crs(crs=proj_crs, inplace=True) 

                if key_field not in working_gdf.columns.tolist():
                    working_gdf = gpd.sjoin(working_gdf, geometry_layer[[key_field, geo_field]], op='within', how='left')

                csd_counts = working_gdf.groupby('CSDUID', dropna=True)['CSDUID'].count()
                csd_counts = tuple(csd_counts[csd_counts > 100].index.tolist())
                if len(csd_counts) > 0:
                    csd_list.append(csd_counts)
            if file.endswith('.gpkg'):
                '''Special code for dealing with geopackages'''
                layer_list = fiona.listlayers(os.path.join(root,file))
                for l in layer_list:
                    if l == 'Parcels':
                        working_gdf = gpd.read_file(os.path.join(root, file), layer=l)
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
                    print(f'Reading in layer: {lyr}')
                    # working_gdf = load_valid_geometry(os.path.join(root, d_path), layer_name=lyr)
                    working_gdf = gpd.read_file(os.path.join(root, d_path), layer=lyr)
                    #working_gdf.set_crs(crs=proj_crs, inplace=True)
                    working_gdf.to_crs(crs=proj_crs, inplace=True)
                    working_gdf = gpd.sjoin(working_gdf, geometry_layer[[key_field, geo_field]], op='within', how='left')

                    csd_counts = working_gdf.groupby('CSDUID', dropna=True)['CSDUID'].count()
                    csd_counts = tuple(csd_counts[csd_counts > 100].index.tolist())
                    if len(csd_counts) > 0:
                        csd_list.append(csd_counts)

    return csd_list

def check_presence(row):
    score = row.sum()
    if score > 0:
        return 1
    else:
        return 0

# ----------------------------------------------------------------------------------------------------------------------
# Inputs

out_path = r'Z:\working\dashboard_work'
csd_path = os.path.join(out_path, 'csd_w_adbl.shp')

source_paths = [r'Z:\working\parcel_sources\parcel_points', r'Z:\working\open_addresses\ca', r'Z:\working\NU_data\merged']

# ----------------------------------------------------------------------------------------------------------------------
# Logic

csd = gpd.read_file(csd_path)
csd.set_crs(crs=4326, inplace=True)
csd_dict = collections.defaultdict(list)

for p in source_paths:
    csd_dict[os.path.split(p)[-1]] = get_coverage(p, csd)
key_list = []
for key in tuple(csd_dict.keys()):
    # explode and calculate var per source
    exploded = explode_list_of_lists(csd_dict[key])
    if (type(exploded) == tuple) and (len(exploded) > 0):
        while type(exploded[0]) == tuple:
            exploded = explode_list_of_lists(exploded)
    csd[key] = csd['CSDUID'].isin(exploded)
    key_list.append(key)

csd['parcels'] = csd[key_list].apply(lambda x: check_presence(x), axis=1)
csd.to_file(os.path.join(out_path, 'csd_w_adblpar.shp'))
print('DONE!')