import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
from numpy.core.numeric import True_
import pandas as pd
from dotenv import load_dotenv
from pandas.core.indexes import multi
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

# ----------------------------------------------------------
# Functions

def measure_road_dist(polygon, roadseg_index, roads):
    ''' Returns the distance to the closest road segment to the building footprint'''
    road = roads[roads.index == int(roadseg_index)] # reduce roads to just those that match the road name
    dist = road.distance(polygon)
    return round(dist.values[0], 4)


def get_road_linkage(bf, road_df, addresses_df):
    
    ''' Returns the road index that matches the following criteria:
    1.) Road name must match in both the road segment and the address point
    2.) adp civic address number must fall within the address range contained for the road segment
    '''
    
    def match_range_address(row, add_val):
        '''returns match or no match based on input range values in row'''
        from_to = []
        # determine number order from lowest to highest into the from to list
        if row[0] > row[1]:
            from_to = [row[1], row[0]]
        if row[0] < row[1]:
            from_to = [row[0], row[1]]
        elif row[0] == row[1]:
            from_to = [row[0], row[1]]
        # determine if add value is within range established in the from to list
        if add_val >= from_to[0] and add_val <= from_to[1]:
            return True
        else: return False
    
    
    adp = addresses_df[addresses_df.index == int(bf['addresses_index'])][['number', 'street']]
    print(adp)
    if len(road_df[road_df['l_nme_cln'] == adp['street'].values[0]]) == 0:
        # PLACEHOLDER in lieu of cleaner road data this will stop name mismatches from getting to from the rest of the comparisons
        return -99999
    
    roadsegs = road_df[road_df['l_nme_cln'] == adp['street'].values[0]]
    
    if len(roadsegs) == 0:
        return np.NaN
    roadsegs['range_match'] = roadsegs[['L_HNUMF', 'L_HNUML']].apply(lambda row: match_range_address(row, adp['number'].values[0]), axis=1)
    roadsegs = roadsegs[roadsegs['range_match'] == True]
    
    if len(roadsegs == 1):
        if type(roadsegs.index.tolist()[0]) != int:
            print(roadsegs.index.tolist()[0])
            sys.exit()
        return int(roadsegs.index.tolist()[0])
    
    elif len(roadsegs) > 1:
        print('Plural return on road index matching check logic')
        print(roadsegs)
        print(adp)
        sys.exit()
        

# ---------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'environments.env'))

pr_gpkg = Path(os.getenv('NT_FINAL_OUTPUT'))
matched_bf_lyr_nme = 'footprint_linkages'

rd_lyr_nme = os.getenv('CLEANED_RD_LYR_NAME')
proj_gpkg = os.getenv('NT_GPKG')
ad_lyr_nme =  'addresses_post_matching'

prj_crs = int(os.getenv('NT_PROJ_CRS'))

# ---------------------------------------------------------
# Logic

print('Step 1. Load in Data')

roads = gpd.read_file(proj_gpkg, layer=rd_lyr_nme, driver='GPKG')
addresses = gpd.read_file(pr_gpkg, layer=ad_lyr_nme, driver='GPKG')
footprints = gpd.read_file(pr_gpkg, layer=matched_bf_lyr_nme, driver='GPKG')

# Set the crs to all match
roads.to_crs(prj_crs, inplace=True)
addresses.to_crs(prj_crs, inplace=True)
footprints.to_crs(prj_crs, inplace=True)

print('Step 2. Apply buisness rules to linked data')
multi_links = footprints.groupby('addresses_index')['addresses_index'].count() # get all counts of adresses_index values
multi_links = multi_links[multi_links > 1] # Keep only values with more than 1 link as we only want to look at that links with more than 1

multi_df = footprints[footprints['addresses_index'].isin(multi_links.index.tolist())]

road_names = list(set(list(addresses[addresses.index.isin(multi_links.index.tolist())]['street']))) # Get all the road names that match the list of road names with multilinks
roads = roads[roads['l_nme_cln'].isin(road_names)] # cut down roads so that only those that we need are retained

not_in_names = addresses[~addresses['street'].isin(list(set(roads['l_nme_cln'].tolist())))]
not_in_names.to_file(pr_gpkg, layer='name_errs')

# Create linkage between the multi df and the roads based on address range and road name
multi_df['road_index'] = multi_df.apply(lambda row: get_road_linkage(row, roads, addresses), axis=1)
multi_df = multi_df[multi_df['road_index'].notnull()]
multi_df['road_index'] = multi_df['road_index'].astype('int32')

multi_df['dist_to_road'] = multi_df[["geometry", 'road_index']].apply(
    lambda row: measure_road_dist(*row, roads), axis=1)

multi_df = multi_df.loc[multi_df.groupby('addresses_index', sort=False)['dist_to_road'].idxmin()] # Return only those records that are the closest to the road segment
multi_df.to_file(pr_gpkg, layer='multi_output')

print('DONE!')
