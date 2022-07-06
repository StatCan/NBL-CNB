from audioop import add
import os
import re
import string
import sys
from pathlib import Path
import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import crs
from shapely import geometry
from shapely.geometry import MultiPolygon, Point, Polygon, geo
from dotenv import load_dotenv
import datetime

from sqlalchemy import false



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

str_types_path = Path(os.getenv('RD_TYPES_TXT_PATH'))

if type(aoi_mask) != None:
    aoi_gdf = gpd.read_file(aoi_mask)

addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf)
footprint = gpd.read_file(bf_path, layer=bf_lyr_nme, mask=aoi_gdf)
linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=aoi_gdf)
footprint.to_crs(crs=proj_crs, inplace=True)
linking_data.to_crs(crs=proj_crs, inplace=True)
addresses.to_crs(crs=proj_crs, inplace=True)
str_types_df = pd.read_csv(str_types_path, delimiter='\t')
str_types_df['Street type'] = str_types_df['Street type'].str.upper()

# -------------------------------------------------------------------------------------------------------------
# NEW CODE

def adp_parcel_compare(address_row, parcel_row):
    '''
    Compares the address data for address points against linked parcels (if available). A full, partial, or false match is determined and a flag of the correct type is
    placed on the record. 

    outputs the following flags:

    0 - No flag on address
    1 - Flag on address
    -1 - Underlying parcel issue (either no underlying parcel or no valid underlying address)

    '''
    
    # For cases where there are no underlying parcel but should be filtered out before being put through this function
    if len(parcel_row) == 0:
        return -1
    
    a_list = address_row.tolist()
    p_list = parcel_row.iloc[0].tolist()

    # if cadastral data has no civic number then we return cad_ncn as no accuracy comparison can ba made
    if not isinstance(p_list[1], str):
        return -1 # cadastral data no civic number

    # parcel (cadastral) and address point address part values in simple vars
    adp_civic = int(a_list[1])
    cad_min = int(p_list[1])
    cad_max = int(p_list[2])
    adp_sname = a_list[2] 
    cad_sname = p_list[3]
    adp_stype = a_list[-1]
    cad_stype = p_list[-1]

    # Setup flag vars as false
    flag_count = 0

    if not (adp_civic >= cad_min) or not (adp_civic <= cad_max):
        flag_count += 1
    if adp_sname != cad_sname:
        flag_count += 1

    if flag_count > 0:
        return 1
    if flag_count == 0:
        return 0

    print(parcel_row)
    print(address_row)
    sys.exit()


def parse_cadastral_address(address_string:str, street_types_dataframe: pd.DataFrame):
    '''
    For parsing the address found in the location field in the pan_ncb. Output is a list in the following format:
    [civic_number_min, civic_number_max, street_name, street_type]
    '''
    
    def determine_min_max(address_string):
        def return_only_numbers(astring):
            '''Takes a string and returns only numbers if applicable else it returns np.NaN'''
            stripped = re.sub("[^0-9]", "", astring)
            if len(address_string) > 0:
                return stripped
            else: return np.NaN

        if len(address_string) == 1:
            return [np.NaN, np.NaN]

        fas = address_string[0]

        if not fas.isdigit():
            return [np.NaN, np.NaN] 

        output_index = 0
        if (address_string[1] == '-') or (address_string[1] == '&') or (address_string[1] == 'to'):
            fas = return_only_numbers(fas)
            sas = return_only_numbers(address_string[2])
            return [fas, sas, 2]

        if any(char.isdigit() for char in fas):
            if ('-' in fas) or ('&' in fas):
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
        # If empty list don't bother looking
        if len(address_string) == 0:
            return np.NaN

        # If all empty strings also don't bother looking
        if sum(len(s) for s in address_string) == 0:
            return np.NaN

        # remove any remaining blank strings
        address_string = [x for x in address_string if len(x) > 0]       

        return ' '.join(address_string)


    def get_street_type(address_string, street_types_dataframe):
        '''
        Returns the address type for the given address as a string
        '''
        if len(address_string) == 0: 
            return [np.NaN, np.NaN]
 
        for i in reversed(address_string):
            i_index = [ind for ind, element in enumerate(address_string) if element == i][-1] # use index for last occurance of the element to avoid erasure of str type like words in street names
            i = i.strip("&/-.")
            # If simple match can be found make it on the abbreviation
            if i in street_types_dataframe.Abbreviation.tolist():
                return [i, i_index]
            # If no simple match can be found check if the type is in unabbreviated form
            if i in  street_types_dataframe['Street type'].tolist():
                i_index = street_types_dataframe.index[street_types_dataframe['Street type'] == i].tolist()[0]
                return [street_types_dataframe.Abbreviation.iloc[i_index], i_index]
            
        return [np.NaN, np.NaN]
    
    if not isinstance(address_string, str):
        return [np.NaN, np.NaN, np.NaN, np.NaN]

    address = address_string.upper()
    a_split = address.split(' ')
    street_name = ''
    # Handle numbers if any
    a_numbers = determine_min_max(a_split)
    address_max = a_numbers[1]
    address_min = a_numbers[0]

    # Remove civic number containing index if necessary
    if (len(a_split) > 2) and (type(a_numbers[0]) != float):  # Don't remove things where there are no numbers in the address data 
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


def address_type_abbreviator(street_type:str, street_types_dataframe: pd.DataFrame):
    '''
    Takes an input street type and returns the abbreviation bas off the street types dataframe
    '''

    street_type = street_type.strip("&/-.")
    # If match can be found on the abbreviation return that
    if street_type in street_types_dataframe.Abbreviation.tolist():
        return street_type
    # If no simple match can be found check if the type is in unabbreviated form
    if street_type in  street_types_dataframe['Street type'].tolist():
        stype_ab = street_types_dataframe.Abbreviation[street_types_dataframe['Street type'] == street_type].tolist()[0]
        return stype_ab


def new_link_finder(address_row, cad_data):
    '''
    Takes records flagged as incorrect and attempt to find a more correct parcel linkage for them. This function will return the a link_field id if there is a more correct
    match or null if no more correct match can be found.
    '''
    
    addr_civic = address_row['number']
    addr_sname = address_row['street']
    addr_stype = address_row['stype_abbr']
    
    new_links = cad_data[(cad_data['address_min'] <= addr_civic) & (cad_data['address_max'] >= addr_civic) & (cad_data['street_name'] == addr_sname)]
    
    if len(new_links) == 0:
        return np.NaN
    if len(new_links) == 1:
        return new_links.link_field.tolist()[0]
    # if len is greater than 1 check to see if the civic value exatly matches the min or max
    if len(new_links) > 1:
        exact_civic = new_links[(new_links['address_min'] == addr_civic) & (new_links['address_max'] == addr_civic)]
        if len(exact_civic) != 0:
            return exact_civic.link_field.tolist()[0]
    print(address_row)
    print(new_links)
    
    sys.exit()

# linking_data = linking_data[linking_data['link_field'] == 15669] 
linking_data['parsed_list'] = linking_data['Location'].apply(lambda location: parse_cadastral_address(location, str_types_df))

linking_data[['address_min', 'address_max', 'street_name', 'street_type']] = pd.DataFrame(linking_data['parsed_list'].tolist(), index= linking_data.index)
addresses['stype_abbr'] = addresses['stype_en'].apply(lambda stype: address_type_abbreviator(stype, str_types_df))

addresses['parcel_location_match'] = addresses[['link_field', 'number', 'street', 'stype_abbr']].apply(lambda row: adp_parcel_compare(row, linking_data[linking_data['link_field'] == row[0]][['link_field', 'address_min', 'address_max', 'street_name', 'street_type']]), axis=1)

flagged_adps = addresses[addresses['parcel_location_match'].isin([1])]
# flagged_adps.to_file(r'C:\projects\point_in_polygon\data\NB_data\parcel_flagging.gpkg', layer='adp_parcel_flagged', driver='GPKG')

print(flagged_adps)

sys.exit()

# check 1 and -1 values to see if the address is elsewhere (results in 5 potential rematches not particularly useful at this time)
false_adps = addresses[addresses['parcel_location_match'].isin([1,-1])]
linking_data = linking_data[~linking_data['address_min'].isna()]
linking_data['address_min'] = linking_data['address_min'].astype(int)
linking_data['address_max'] = linking_data['address_max'].astype(int)

# false_adps = false_adps[false_adps['CIV_ID'] == '{A4D224D7-41ED-4099-81CD-103B90B7EA2D}'] # Test record 20 Birch Cres

false_adps['correct_linkage'] = false_adps[['number', 'street', 'stype_abbr']].apply(lambda row: new_link_finder(row, linking_data[['link_field', 'address_min', 'address_max', 'street_name', 'street_type']]), axis=1)
print(len(false_adps))
print(false_adps[~false_adps['correct_linkage'].isna()].head())
print(len(false_adps[~false_adps['correct_linkage'].isna()].head()))
addresses[addresses['parcel_location_match'].isin([1,-1])].to_file(r'C:\projects\point_in_polygon\data\NB_data\parcel_flagging.gpkg', layer='adp_parcel_flagged', driver='GPKG')
print('DONE!')
