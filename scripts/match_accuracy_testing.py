from cmath import nan
import logging
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import fiona
import re
import shapely
import sys
from pathlib import Path
from dotenv import load_dotenv
from bisect import bisect
from collections import OrderedDict
from operator import add, index, itemgetter
from shapely import geometry
from shapely.geometry import Point, Polygon, MultiPolygon
sys.path.insert(1, os.path.join(sys.path[0], ".."))
import helpers
import datetime

'''
Test the accuracy of the matching script on a case by case basis (one to one, many to many, etc). Clean and match the address in the building with the address on the point to 
determine the accuracy of the match. Return metrics on the number of correct matches and the number of false postives. Also return the match layer with the point matches valdated so 
that they can be visually inspected to determine logic improvements

    Stages:
            1.) Clean address data on footprints so that it matches the format found in the address data
            2.) Load in the address data and compare its address data against the data found in its matched footprint by checking the following address components:
                a.) Address number is equal to or greater than the address range minimum
                b.) Address number is equal to or less than the address range maximum
                c.) Street name is a match between the address point and building footprint
                d.) Street type is a match between the address point and building footprint
            3.) Flag bad matches and verify good matches
            4.) Generate accuracy metrics and export output files

'''

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Functions

def bf_address_match(address, street_types_dataframe):
    '''Unique to the Fredericton open building data. Convert the address field into its component parts and output as a list in the following order:
    [Address_Min, Address_Max, Street_Name, Street_Typ]'''
   
    def determine_min_max(address_string):
        def return_only_numbers(astring):
            '''Takes a string and returns only numbers if applicable else it returns np.NaN'''
            stripped = re.sub("[^0-9]", "", astring)
            if len(address_string) > 0:
                return stripped
            else: return np.NaN

        fas = address_string[0]
        output_index = 0
        if any(char.isdigit() for char in fas):
            if '-' in fas:
                fas_split = fas.split('-')
                fas_split = [return_only_numbers(f) for f in fas_split]
                return [min(fas_split), max(fas_split), output_index]
            else:
                fas = return_only_numbers(fas)
                if isinstance(fas, str):
                    return [fas, fas, output_index]
                else: return [fas, fas, np.NaN]
                
        else:
            return [np.NaN, np.NaN, np.NaN]

    def get_street_name(address_string):
        '''
        Returns the name of the street from the address string
        '''
        # If empty list don't both looking
        if len(address_string) == 0:
            return np.NaN

        # If all empty strings also don't bother looking
        if sum(len(s) for s in address_string) == 0:
            return np.NaN

        # remove any remaining blank strings
        address_string = [x for x in address_string if len(x) > 0]       

        return ''.join(address_string)


    def get_street_type(address_string, street_types_dataframe):
        '''
        Returns the address type for the given address as a string
        '''
        if len(address_string) == 0: 
            return [np.NaN, np.NaN]
 
        for i in reversed(address_string):
            i_index = address_string.index(i)
            i = i.strip("&/-.")
            # If simple match can be found make it on the abbreviation
            if i in street_types_dataframe.Abbreviation.tolist():
                return [i, i_index]

            # If no simple match can be found check if the type is in unabbreviated form
            if i in  street_types_dataframe['Street type'].tolist():
                i_index = street_types_dataframe.index[street_types_dataframe['Street type'] == i].tolist()[0]
                return [street_types_dataframe.Abbreviation.iloc[i_index], i_index]
            
        return [np.NaN, np.NaN]

    address = address.upper()
    a_split = address.split(' ')
    pure_a_split = a_split
    street_name = ''
    # Handle numbers if any
    a_numbers = determine_min_max(a_split)
    address_max = a_numbers[1]
    address_min = a_numbers[0]

    # Remove civic number containing index if necessary
    if isinstance(a_numbers[2], int):
        a_split = a_split[a_numbers[2] + 1:]

    # Extract Street Type
    stype_list = get_street_type(a_split, street_types_dataframe)
    street_type = stype_list[0]

    # Remove street type index if necessary
    if isinstance(street_type, str):
        a_split = a_split[:stype_list[1]]
    
    street_name = get_street_name(a_split)

    out_list = [address_min, address_max, street_name, street_type]      
    return out_list


def abbreviate_street_type(stype, st_type_key_df):

    '''
    Returns an abbreviated version of the given street name if possible based off the given formatting key in df form
    '''
    filtered_key = st_type_key_df[st_type_key_df['Street type'] == stype.upper()]
    if len(filtered_key) == 1:
        return filtered_key['Abbreviation'].tolist()[0]

    print(st_type_key_df[st_type_key_df['Street type'] == stype.upper()])
    print(stype)
    sys.exit()


def match_range_address(bf_index, add_val, bf_df):
        '''returns match or no match based on input range values in row'''
        # determine if add value is within range established in the from to list
        link_row = bf_df.iloc[int(bf_index)]
        if not isinstance(link_row['address_min'], str):
            return np.NaN
        add_rng_max = int(link_row['address_max'])
        add_rng_min = int(link_row['address_min'])
        if add_val >= add_rng_min and add_val <= add_rng_max:
            return True
        else: return False

def match_street_name(bf_index, str_nme, bf_df):
    '''returns match or no match between the adp street name and the matched street name in the building footprints'''
    link_row = bf_df.iloc[int(bf_index)]
    if not isinstance(link_row['street_name'], str) or not isinstance(str_nme, str):
            return np.NaN

    if str_nme == link_row['street_name']:
        return True
    else:
        return False


def match_street_typ(bf_index, str_typ, bf_df):
    '''returns match or no match between the adp street type and the matched street type in the building footprints'''
    link_row = bf_df.iloc[int(bf_index)]
    if not isinstance(link_row['street_type'], str) or not isinstance(str_typ, str):
            return np.NaN
    link_str_type = link_row['street_type'].strip(' ')
    if str_typ == link_str_type:
        return True
    else:
        # print(str_typ)
        # print(link_str_type)
    
        return False


def match_flagger(adr_flag, stn_flag, stt_flag):
    '''Determines if a match is Full, Partial, or False based on the results from the address, street name,  and street type flag'''
    # All NaN skip match check
    if not isinstance(adr_flag, bool) and not isinstance(stn_flag, bool) and not isinstance(stt_flag, bool):
        return np.NaN
    match_quality = sum([adr_flag, stn_flag, stt_flag])

    if match_quality == 3:
        return 'FULL'
    if (match_quality < 3) and (match_quality > 0):
        return 'PARTIAL'
    if match_quality == 0:
        return 'FALSE'  


# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

output_path = os.getcwd()

matched_ap_gpkg = Path(os.getenv('MATCHED_OUTPUT_GPKG'))

aoi_mask = Path(os.getenv('AOI_MASK'))

footprint_gpkg = Path(os.getenv('DATA_GPKG'))
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')

proj_crs = int(os.getenv('PROJ_CRS'))

str_types_path = Path(os.getenv('RD_TYPES_TXT_PATH'))

# Address fields for inputs
bf_address_fields = 'Prop_Loc' # convert to list in future if needed

bf_link_field = 'footprint_index'
 
m_acc_gpkg_path = Path(os.getenv('MATCH_ACC_GPKG'))

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Logic

# Load in data and prep

aoi_gdf = gpd.read_file(aoi_mask)

str_types_df = pd.read_csv(str_types_path, delimiter='\t')
str_types_df['Street type'] = str_types_df['Street type'].str.upper()

footprint = gpd.read_file(footprint_gpkg, layer=footprints_lyr_nme, crs=26911, mask=aoi_gdf)
footprint.to_crs(crs=proj_crs, inplace=True)

# Clean and prep the address data in the inputs

# Footprint address field cleaning
footprint['address_components'] = footprint[bf_address_fields].apply(lambda bf_address: bf_address_match(bf_address, str_types_df))
footprint[['address_min', 'address_max', 'street_name', 'street_type']] = pd.DataFrame(footprint['address_components'].tolist(), index= footprint.index)
footprint.drop(columns=['address_components'], inplace= True)

for t in fiona.listlayers(matched_ap_gpkg):
    out_gpkg_nme = '_'.join(t.split('_', -2))
    print(f'Running analysis on {t}')
    addresses = gpd.read_file(matched_ap_gpkg, layer=t, driver='GPKG', mask=aoi_gdf)
    addresses = addresses[~addresses['footprint_index'].isna()]
    print()
    # Address points address field cleaning/prep
    addresses['type_en_abv'] = addresses['ST_TYPE_E'].apply(lambda x: abbreviate_street_type(x, str_types_df))

    addresses['ad_rng_check'] = addresses[['footprint_index', 'number']].apply(lambda x: match_range_address(x['footprint_index'], x['number'], footprint), axis=1)
    addresses['str_nme_check'] = addresses[['footprint_index', 'street']].apply(lambda x: match_street_name(x['footprint_index'], x['street'], footprint), axis=1)
    addresses['str_typ_check'] = addresses[['footprint_index', 'type_en_abv']].apply(lambda x: match_street_typ(x['footprint_index'], x['type_en_abv'], footprint), axis=1)

    addresses['match_flag'] = addresses.apply(lambda x: match_flagger(x['ad_rng_check'], x['str_nme_check'], x['str_typ_check']), axis=1)

    # print(addresses[['footprint_index','number', 'street','type_en_abv', 'ad_rng_check', 'str_nme_check', 'str_typ_check', 'match_flag']].head())
    # print(footprint.iloc[[1608, 719, 8938, 20477, 2770]])

    match_counts = addresses['match_flag'].value_counts()
    print(t)
    print(match_counts)
    unique_counts = []
    for f in ['FULL', 'PARTIAL', 'FALSE']:
        unique_counts.append(len(list(set(addresses[addresses['match_flag'] == f]['ADDR_SYM'].tolist()))))
        addresses[addresses['match_flag'] == f].to_file(os.path.join(m_acc_gpkg_path, f'{out_gpkg_nme}.gpkg'), layer=f'{f.lower()}_flags', driver='GPKG')
    print('UNIQUE ADDRESS COUNTS')
    print(f'FULL: {unique_counts[0]}')
    print(f'PARTIAL: {unique_counts[1]}')
    print(f'FALSE: {unique_counts[2]}')
print('DONE!')