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

pd.options.mode.chained_assignment = None # Gets rid of annoying warning

# ------------------------------------------------------------------------------------------------
# Functions

def reproject(ingdf, output_crs):
    ''' Takes a gdf and tests to see if it is in the projects crs if it is not the funtions will reproject '''
    if ingdf.crs == None:
        ingdf.set_crs(epsg=output_crs, inplace=True)    
    elif ingdf.crs != f'epsg:{output_crs}':
        ingdf.to_crs(epsg=output_crs, inplace=True)
    return ingdf


def getXY(pt):
    return (pt.x, pt.y)


def records(filename, usecols, **kwargs):
    ''' Allows for importation of file with only the desired fields must use from_features for importing output into geodataframe'''
    with fiona.open(filename, **kwargs) as source:
        for feature in source:
            f = {k: feature[k] for k in ['id', 'geometry']}
            f['properties'] = {k: feature['properties'][k] for k in usecols}
            yield f


def str_type_cln(street_name, correction_dict):
    '''Cleans the street types so that they are standardized across all datasets returns the corrected street type in upper case'''
    street_name = street_name.upper()
    street_split = street_name.split()
    
    # If single word or empty return the name as is
    if (street_split == 1 or street_split == 0):
        return street_name

    s_type = street_split[-1]
    type_index = street_split.index(s_type)
    
    # If last word is a direction take the second last word
    if (len(s_type) == 1 or len(s_type) == 2) and (s_type in ['N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'O', 'SO']):
        s_type = street_split[-2]
        type_index = street_split.index(s_type)
    
    # ensure that street type conforms to the correct appreviation as outlined in the list
    if s_type in correction_dict:
        s_type = correction_dict[s_type]
    
    #Put the cleaned street name back together
    street_split[type_index] = s_type
    cleaned_name = " ".join(street_split)
    
    return cleaned_name
    

def road_partitioner(address: string):
    '''Takes a road string which possibly containes name, type and direction and converts it into a list of parts based off of master lists of road types'''
    
    def determiner(in_string, check_list):
        ''' Determines if string is in input list. If it is then returns the value as a string else it will return np.nan'''
        output = [i for i in check_list if in_string == i]
        
        if len(output) == 0:
            return np.nan
        
        return output[0]

    type_abbrev = ['ABBEY', 'ACRES', 'ALLÉE', 'ALLEY', 'AUT', 'AVE', 'AV', 'BAY', 'BEACH', 'BEND', 'BLVD', 'BOUL', 'BYPASS', 'BYWAY', 'CAMPUS', 'CAPE', 'CAR', 
            'CARREF', 'CTR', 'C', 'CERCLE', 'CHASE', 'CH', 'CIR', 'CIRCT', 'CLOSE', 'COMMON', 'CONC', 'CRNRS', 'CÔTE', 'COUR', 'COURS', 'CRT', 'COVE', 'CRES', 
            'CROIS', 'CROSS', 'CDS', 'DALE', 'DELL', 'DIVERS', 'DOWNS', 'DR', 'ÉCH', 'END', 'ESPL', 'ESTATE', 'EXPY', 'EXTEN', 'HWY', 'PINES','PL', 'PLACE', 'PLAT', 
            'PLAZA', 'PT', 'POINTE', 'PORT', 'PVT', 'PROM', 'QUAI', 'QUAY', 'RAMP', 'RANG', 'RG', 'RIDGE', 'RISE', 'RD', 'RDPT', 'RTE', 'ROW', 'RUE', 'RLE', 
            'RUN', 'SENT', 'SQ', 'ST', 'SUBDIV', 'TERR', 'TSSE', 'THICK', 'TOWERS', 'TLINE', 'TRAIL', 'TRNABT', 'VALE', 'VIA', 'VIEW', 'VILLGE', 'VILLAS', 
            'VISTA', 'VOIE', 'WALK', 'WAY', 'WHARF', 'WOOD', 'WYND']
    directions = [' N ', ' S ', ' E ', ' W ', ' NE ', ' SE ', ' NW ', ' SW ', ' O ', ' NO ', ' SO ']

    # If available find the roads alt name in the adress and assign it to the correct vars. Slice out the address after
    alt_name = np.nan
    alt_type = np.nan
    alt_name_full = np.nan

    if address.find('(') != -1:
        s_index = address.index('(')+1
        c_index = address.index(')')
        alt_full = address[s_index : c_index].split(' ')
        alt_name_full = address[s_index : c_index]
        alt_type =  determiner(alt_full[-1], type_abbrev)
        if type(alt_type) == str: del alt_full[-1]

        alt_name = ' '.join(alt_full)

        # Slice out the alt string from the address
        address = address[0 : address.index('(') : ] + address[address.index(')') + 1 : :].rstrip() 
    
    # Split into component parts and filter out 0 len strings
    add_parts = address.split(' ')
    add_parts = list(filter(len, add_parts))

    # Grab the directio from the end of the road
    direction = determiner(add_parts[-1], directions)
    if type(direction) == str: del add_parts[-1]
    
    # Grab the road type
    rtype = determiner(add_parts[-1], type_abbrev)
    if type(rtype) == str: del add_parts[-1]    

    # Compile the full road name
    str_nme = ' '.join(add_parts)
    str_nme_full = []
    for f in [str_nme, rtype, direction]:
        if type(f) == str:
            str_nme_full.append(f)
    str_nme_full = ' '.join(str_nme_full)

    return [str_nme, rtype, direction, alt_name, alt_type, alt_name_full, str_nme_full]    


def return_smallest_match(ap_matches, parcel_df, unique_id):
    '''Takes plural matches of buildings or address points and compares them against the size of the matched parcel. Returns only the smallest parcel that was matched'''
    ap_matches['ap_match_id'] = range(1, len(ap_matches.index)+1)
    o_ids = []
    for rid in list(set(ap_matches[unique_id].tolist())):
        rid_matches = ap_matches[ap_matches[unique_id] == rid]
        rid_ids = list(set(rid_matches['link_field'].tolist()))
        match_parcels = parcel_df[parcel_df['link_field'].isin(rid_ids)]
        match_parcels.sort_values(by=['AREA'], inplace=True, ascending=True)
        min_parcel_link = match_parcels['link_field'].tolist()[0]
        o_ids.append(rid_matches[rid_matches['link_field'] == min_parcel_link].ap_match_id.tolist()[0])
    ap_matches = ap_matches[ap_matches['ap_match_id'].isin(o_ids)]
    ap_matches.drop(columns=['ap_match_id'], inplace=True)
    return ap_matches
    

def shed_flagging(footprint_gdf, address_gdf, linking_gdf):
    '''
    Methodology for flagging buildings as sheds
    '''
    
    def find_sheds( bf_data, ap_count, bf_area_field='bf_area', bf_index_field='bf_index', bp_threshold=20, min_adressable_area=50, max_shed_size=100):
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
            sheds = bf_data.loc[bf_data[bf_area_field] < min_adressable_area]
            shed_indexes = sheds[bf_index_field].values.tolist() # convert to list of indexes
            return shed_indexes

        # Take out the tiny buildings under 50m2 and prelabel them as sheds then take remainder and test count vs count
        sheds = pd.DataFrame(bf_data.loc[bf_data[bf_area_field] < min_adressable_area])
        bf_data = bf_data.loc[(bf_data[bf_area_field] > min_adressable_area)]

        bf_count = len(bf_data) # reset bf_count because we changed the # of buildings in bf_data

        ap_bf_diff = bf_count - ap_count # how many more bf's there are than address points in the parcel
        sheds = pd.concat([sheds, bf_data.sort_values(bf_area_field, ascending=True).head(ap_bf_diff)], axis=0, join='outer') # sort the smallest to the top then take the top x rows based on ap_bf_diff value 
        
        sheds = sheds[sheds[bf_area_field] <= max_shed_size] # remove things from the output that are unlikly to be sheds >= 100m2

        shed_indexes = sheds[bf_index_field].values.tolist() # convert to list of indexes
        return shed_indexes

    adp_parcel_linkages = address_gdf.groupby('link_field', dropna=True)['link_field'].count()
    bf_parcel_linkages = footprint_gdf.groupby('link_field', dropna=True)['link_field'].count()

    # Return only cases where the bf count is higher than the adp count
    adp_parcel_l_bf = adp_parcel_linkages[adp_parcel_linkages.index.isin(bf_parcel_linkages.index.tolist())]
    bf_parcel_l_ap = bf_parcel_linkages[bf_parcel_linkages.index.isin(adp_parcel_linkages.index.tolist())]

    bf_parcel_l_ap = pd.DataFrame(bf_parcel_l_ap)
    bf_parcel_l_ap.rename(columns={ bf_parcel_l_ap.columns[0]: "bf_count"}, inplace=True)

    adp_parcel_l_bf = pd.DataFrame(adp_parcel_l_bf)
    adp_parcel_l_bf.rename(columns={adp_parcel_l_bf.columns[0]: "ap_count"}, inplace=True)

    linking_gdf = linking_gdf.loc[linking_gdf['link_field'].isin(bf_parcel_l_ap.index.tolist())]
    linking_gdf['shed_list'] = linking_gdf['link_field'].apply(lambda x: find_sheds(footprint_gdf[footprint_gdf['link_field'] == x], adp_parcel_l_bf[adp_parcel_l_bf.index == x].ap_count.tolist()[0]))
    shed_indexes = [ i for l in linking_gdf['shed_list'].tolist() for i in l ] # item for sublist in t for item in sublist: t being the shed_list list

    shed_gdf = footprint_gdf[footprint_gdf['bf_index'].isin(shed_indexes)]
    footprint_gdf = footprint_gdf.loc[~footprint_gdf['bf_index'].isin(shed_indexes)]

    shed_gdf['shed_flag'] = True
    footprint_gdf['shed_flag'] = False

    footprint_gdf = footprint_gdf.append(shed_gdf)
    return footprint_gdf


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
        output_index = 0

        if '-' in address_string[0]:
            # if there is a dash between number without spaces split the string on the dash
            split_string = address_string[0].split('-')
            fas = split_string[0]
            sas = split_string[-1]
        
        if not fas.isdigit():
            return [np.NaN, np.NaN]

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
    if type(street_type) != string:
        return None
    street_type = street_type.strip("&/-.")
    # If match can be found on the abbreviation return that
    if street_type in street_types_dataframe.Abbreviation.tolist():
        return street_type
    # If no simple match can be found check if the type is in unabbreviated form
    if street_type in  street_types_dataframe['Street type'].tolist():
        stype_ab = street_types_dataframe.Abbreviation[street_types_dataframe['Street type'] == street_type].tolist()[0]
        return stype_ab


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


# ------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

geo_crs = os.getenv('CRS')
proj_crs = os.getenv('PROJ_CRS')

footprint_lyr = Path(os.getenv('BF_PATH'))
footprint_lyr_name = os.getenv('BF_LYR_NME')

ap_path = Path(os.getenv('ADDRESS_PATH'))
ap_lyr_nme = os.getenv('ADDRESS_LAYER')

ap_add_fields = ['CIVIC_NUM', 'STREET', 'ST_TYPE_E', 'ADDR_DESC', 'geometry'] # geoNB fields ['CIVIC_NUM', 'STREET_NAME', 'ST_TYPE_CD', 'ST_NAME_COMPLETE', 'geometry']
ap_type_cds = Path(os.getenv('ADDRESS_TYPE_CODES'))

linking_data_path = Path(os.getenv('LINKING_PATH'))
linking_lyr_nme = os.getenv('LINKING_LYR_NME')

linking_ignore_columns = os.getenv('LINKING_IGNORE_COLS') 

# road types txt
str_types_path = Path(os.getenv('RD_TYPES_TXT_PATH'))

# AOI mask if necessary
aoi_mask = os.getenv('AOI_MASK')

# output gpkg
project_gpkg = Path(os.getenv('DATA_GPKG'))
rd_crs = os.getenv('RD_CRS')

# ------------------------------------------------------------------------------------------------
# Logic

# Load dataframes.
aoi_gdf = None
if aoi_mask != None:
    aoi_gdf = gpd.read_file(aoi_mask)

str_types_df = pd.read_csv(str_types_path, delimiter='\t')
str_types_df['Street type'] = str_types_df['Street type'].str.upper()

print('Loading in linking data')
linking_data = gpd.read_file(linking_data_path, layer=linking_lyr_nme, linking_ignore_columns=linking_ignore_columns, mask=aoi_gdf)
linking_cols_drop = linking_data.columns.tolist()
linking_data['link_field'] = range(1, len(linking_data.index)+1)
linking_data['AREA'] = linking_data['geometry'].area
linking_data = linking_data[linking_data['AREA'] > 101]
linking_data = reproject(linking_data, proj_crs)

for col in ['geometry', 'Pan_Int', 'Location']:
    linking_cols_drop.remove(col)

linking_data.drop(columns=linking_cols_drop, inplace=True)

linking_data['parsed_list'] = linking_data['Location'].apply(lambda location: parse_cadastral_address(location, str_types_df))

linking_data[['address_min', 'address_max', 'street_name', 'street_type']] = pd.DataFrame(linking_data['parsed_list'].tolist(), index= linking_data.index)
linking_data.drop(columns=['parsed_list'], inplace=True)

linking_data.to_file(project_gpkg, layer='parcels_cleaned', driver='GPKG')

print('Loading in address data')
if os.path.split(ap_path)[-1].endswith('.csv'):
    addresses = pd.read_csv(ap_path)
    addresses = gpd.GeoDataFrame(addresses, geometry=gpd.points_from_xy(addresses.longitude, addresses.latitude))
else:
    addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf)

print('Cleaning and prepping address points')

# addresses = addresses[ap_add_fields]
addresses = reproject(addresses, proj_crs)
addresses = gpd.sjoin(addresses, linking_data, op='within', how='left')

# Deal with duplications in the address  layer caused by the spatial join. Take the smallest parcel as assumed to be the most accurate
grouped = addresses.groupby('CIV_ID', dropna=True)['CIV_ID'].count()
grouped = grouped[grouped > 1].index.tolist()
addresses_plural_sj = addresses[addresses['CIV_ID'].isin(grouped)]
addresses_singular = addresses[~addresses['CIV_ID'].isin(grouped)]
addresses_plural_sj = return_smallest_match(addresses_plural_sj, linking_data, 'CIV_ID')
addresses = addresses_singular.append(addresses_plural_sj)

for f in ['index_right', 'index_left']:
    if f in addresses.columns.tolist():
        addresses.drop(columns=f, inplace=True)

addresses['a_id'] = addresses.index
addresses["number"] = addresses[ap_add_fields[0]].map(int)
addresses['street'] = addresses[ap_add_fields[1]].str.upper()
addresses['stype_en'] =addresses[ap_add_fields[2]].str.upper()
# none_stype = addresses[addresses['stype_en'] == None]
# addresses = addresses[~addresses['stype_en'] == None]
addresses['stype_abbr'] = addresses['stype_en'].apply(lambda stype: address_type_abbreviator(stype, str_types_df))
# addresses = addresses.append(none_stype)
addresses.drop(columns=[ap_add_fields[0], ap_add_fields[1], ap_add_fields[2]], inplace=True)

addresses['parcel_location_match'] = addresses[['link_field', 'number', 'street', 'stype_abbr']].apply(lambda row: adp_parcel_compare(row, linking_data[linking_data['link_field'] == row[0]][['link_field', 'address_min', 'address_max', 'street_name', 'street_type']]), axis=1)


print('Exporting cleaned address dataset')
addresses.to_file(project_gpkg, layer='addresses_cleaned', driver='GPKG')

print('Loading in footprint data')
footprint = gpd.read_file(footprint_lyr, layer=footprint_lyr_name ,mask=aoi_gdf)

footprint = reproject(footprint, proj_crs)

footprint['geometry'] = footprint['geometry'].buffer(0)

print('Cleaning and prepping footprint data')
# footprint = explode(footprint) # Remove multipart polygons convert to single polygons
footprint['bf_area'] = footprint['geometry'].area
# footprint = footprint.loc[footprint.area >= 20.0] # Remove all buildings with an area of less than 20m**2
footprint = footprint.reset_index()
footprint.rename(columns={'index':'bf_index'}, inplace=True)
footprint.set_index(footprint['bf_index'])
footprint = reproject(footprint, proj_crs)

footprint['centroid_geo'] = footprint['geometry'].apply(lambda pt: pt.centroid)
footprint = footprint.set_geometry('centroid_geo')
footprint = gpd.sjoin(footprint, linking_data, how='left', op='within')
footprint.drop(columns=['AREA'], inplace=True)
grouped_bf = footprint.groupby('bf_index', dropna=True)['bf_index'].count()
grouped_bf = grouped_bf[grouped_bf > 1].index.tolist()
footprint_plural_sj = footprint[footprint['bf_index'].isin(grouped_bf)]
footprint_singular = footprint[~footprint['bf_index'].isin(grouped_bf)]
footprint_plural_sj = return_smallest_match(footprint_plural_sj, linking_data, 'bf_index')
footprint = footprint_singular.append(footprint_plural_sj)

footprint = shed_flagging(footprint, addresses, linking_data)

footprint = footprint.set_geometry('geometry')
footprint.drop(columns=['centroid_geo'], inplace=True)

for f in ['index_right', 'index_left']:
    if f in footprint.columns.tolist():
        footprint.drop(columns=f, inplace=True)

print('Exporting cleaned dataset')
footprint.to_file(project_gpkg, layer='footprints_cleaned', driver='GPKG')

end_time = datetime.datetime.now()
print(f'Start Time: {start_time}')
print(f'End Time: {end_time}')
print(f'Total Runtime: {end_time - start_time}')
print('DONE!')