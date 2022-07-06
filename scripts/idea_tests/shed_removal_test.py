import os
import re
import string
import sys
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
from numpy.core.numeric import True_
import pandas as pd
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo
from dotenv import load_dotenv
import datetime

from sqlalchemy import false


def find_sheds( bf_data, ap_count, bf_area_field='bf_area', bf_index_field='bf_index', bp_threshold=20):
    '''
    returns a list of all bf_indexes that should be flagged as sheds and should be considered unaddressable.
    take the difference from the counts of each type of record in the parcel and flag the number of smallest
    buildings that coorespond with the difference value
    '''
    bf_count = len(bf_data)
    
    # If either is equal to zero this method will not help select out sheds
    if ap_count == 0 or bf_count == 0:
        return []
    if bf_count == 1:
        return []

    # Sizing is different in trailer parks so deal with these differently
    if bf_count > bp_threshold:
        # do just the tiny building check as the min max between home and shed in these areas overlaps
        sheds = bf_data.loc[bf_data[bf_area_field] < 50]
        shed_indexes = sheds[bf_index_field].values.tolist() # convert to list of indexes
        return shed_indexes

    # Take out the tiny buildings under 50m2 and prelabel them as sheds then take remainder and test count vs count
    sheds = bf_data.loc[bf_data[bf_area_field] < 50]
    bf_data = bf_data.loc[(bf_data[bf_area_field] > 50)]

    bf_count = len(bf_data) # reset bf_count because we changed the # of buildings in bf_data

    ap_bf_diff = bf_count - ap_count # how many more bf's there are than address points in the parcel
    sheds = sheds.append(bf_data.sort_values(bf_area_field, ascending=True).head(ap_bf_diff)) # sort the smallest to the top then take the top x rows based on ap_bf_diff value 
    
    sheds = sheds[sheds[bf_area_field] <= 100] # remove things from the output that are unlikly to be sheds >= 100m2

    shed_indexes = sheds[bf_index_field].values.tolist() # convert to list of indexes
    return shed_indexes    

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))
bf_path =  Path(os.getenv('DATA_GPKG'))
bf_lyr_nme = 'footprints_cleaned'
# bf_lyr_nme = 'footprint_linkages'

ap_path = Path(os.getenv('DATA_GPKG'))
ap_lyr_nme = 'addresses_cleaned'

linking_data_path = Path(os.getenv('DATA_GPKG'))
linking_lyr_nme = 'parcels_cleaned'

aoi_mask = Path(os.getenv('AOI_MASK'))
proj_crs = int(os.getenv('PROJ_CRS'))

if type(aoi_mask) != None:
    aoi_gdf = gpd.read_file(aoi_mask)

addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf)
footprint = gpd.read_file(bf_path, layer=bf_lyr_nme, mask=aoi_gdf)
linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=aoi_gdf)
footprint.to_crs(crs=proj_crs, inplace=True)
linking_data.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs=proj_crs, inplace=True)

# -------------------------------------------------------------------------------------------------------------
# Test of building removal alex's method
# get counts by parcel id
adp_parcel_linkages = addresses.groupby('link_field', dropna=True)['link_field'].count()
bf_parcel_linkages = footprint.groupby('link_field', dropna=True)['link_field'].count()

# Return only cases where the bf count is higher than the adp count
adp_parcel_l_bf = adp_parcel_linkages[adp_parcel_linkages.index.isin(bf_parcel_linkages.index.tolist())]
bf_parcel_l_ap = bf_parcel_linkages[bf_parcel_linkages.index.isin(adp_parcel_linkages.index.tolist())]

bf_parcel_l_ap = pd.DataFrame(bf_parcel_l_ap)
bf_parcel_l_ap.rename(columns={ bf_parcel_l_ap.columns[0]: "bf_count"}, inplace=True)

adp_parcel_l_bf = pd.DataFrame(adp_parcel_l_bf)
adp_parcel_l_bf.rename(columns={adp_parcel_l_bf.columns[0]: "ap_count"}, inplace=True)

linking_data = linking_data.loc[linking_data['link_field'].isin(bf_parcel_l_ap.index.tolist())]
linking_data['shed_list'] = linking_data['link_field'].apply(lambda x: find_sheds(footprint[footprint['link_field'] == x], adp_parcel_l_bf[adp_parcel_l_bf.index == x].ap_count.tolist()[0]))
shed_indexes = [ i for l in linking_data['shed_list'].tolist() for i in l ] # item for sublist in t for item in sublist: t being the shed_list list

shed_gdf = footprint[footprint['bf_index'].isin(shed_indexes)]
footprint = footprint.loc[footprint['bf_index'].isin(shed_indexes)]

shed_gdf['shed_flag'] = True
footprint['shed_flag'] = False

footprint = footprint.append(shed_gdf)

# --------------------------------------------------------------------------------------------------------
# TEST OUTPUT AREA DO NT COPY OVER

print(shed_gdf[shed_gdf['OBJECTID'] == 20171])


shed_gdf.to_file(r'C:\projects\point_in_polygon\data\NB_data\data.gpkg', layer='iter_shed_test')

print('DONE!')
