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

def bf_address_match(address):
    '''Unique to the Fredericton open building data. Convert the address field into its component parts and output as a list in the following order:
    [Address_Min, Address_Max, Street_Name, Street_Typ]'''
    
    def determine_min_max(address_string):
        '''
        returns the min and max values of an input address string in cases where only 1 address is available will return the same number as both the address min and max
        '''

        if len(address_string) == 2:
            return [np.NaN, np.NaN]

        # If the first item in the list is numeric it is the address number
        if address_string[0].strip("&AB").isnumeric():
            a_max = address_string[0].strip("&AB")
            a_min = address_string[0].strip("&AB")
            return [a_min, a_max]

        # Records with a range of values in it (format int-int) need to be split and the min max values determined
        num_split = address_string[0].split('-')
        if (len(num_split) == 2) and (num_split[0].strip("&AB").isnumeric()) and (num_split[1].strip("&AB").isnumeric()):
            num_1 = num_split[0].strip("&AB")       
            num_2  = num_split[1].strip("&AB")
            if int(num_2) > int(num_1):
                return [num_1, num_2]
            else: 
                return [num_2, num_1]
        
        if len(num_split) == 3:
            # For those cases with three number strings for example (86-92-94 St Marys St) take biggest and smallest #'s middle values will be caught in the range
            int_list = [int(n) for n in num_split]
            return [max(int_list), min(int_list)]

        if len(num_split) == 1:
            # cases without #'s longer than 2 items ex. (Carleton Ward (Rear))
            return [np.NaN, np.NaN]

        # if len(num_split) > 2 and all(n.isnumeric() for n in num_split):
            
        
        print(address_string)
        print(num_split)
        print(address)
        return [np.NaN, np.NaN] 

    a_split = address.split(' ')
    
    address_max = ''
    address_min = ''
    street_name = ''
    street_type = ''

    # Handle numbers if any
    a_numbers = determine_min_max(a_split)
    address_max = a_numbers[1]
    address_min = a_numbers[0]

    out_list = [address_min, address_max, street_name, street_type]      
    return out_list


    print(a_split)
    
    sys.exit()

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Inputs

start_time = datetime.datetime.now()

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))

output_path = os.getcwd()

matched_ap_gpkg = Path(os.getenv('MATCHED_OUTPUT_GPKG'))

footprint_gpkg = Path(os.getenv('DATA_GPKG'))
footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')

proj_crs = int(os.getenv('PROJ_CRS'))

# Address fields for inputs
bf_address_fields = 'Prop_Loc' # convert to list in future if needed

# ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Logic

footprint = gpd.read_file(footprint_gpkg, layer=footprints_lyr_nme, crs=26911)
footprint.to_crs(crs=proj_crs, inplace=True)

#addresses = gpd.read_file(matched_ap_gpkg, layer='ap_one_to_one_bf_links', driver='GPKG')

# Clean and prep the address data in the inputs

# Footprint address cleaning
footprint['address_components'] = footprint[bf_address_fields].apply(lambda bf_address: bf_address_match(bf_address))


print('DONE!')