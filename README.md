# points_to_polygons_PoC

## Description and Sources
Proof of concept for points into polygons to add address data to the building footprint. Yellowknife was used as a testing ground due to data availability and familiarity. 

The work done in this project is based off work off JesseStewart1's original work for the NRN prject can be found here: https://github.com/jessestewart1/nrn-rrn/blob/development/src/stage_1/segment_addresses.py 

Demonstration jupyter notebook for Jesse's code con be found here: https://github.com/jessestewart1/nrn-rrn/blob/master/reports/address_segmentation.html

All data for this project downloaded from the Yellowknife Open Data Portal civic addresses and building footprint Jan 10th 2021 vintage. The data can be found in the yellowknife open data portal at the following link:
http://opendata.yellowknife.ca/

### Layers Used:
- Civic Addresses
- Building Footprints
- Property Parcels

### This project was built in python using the following modules (list can also be found in the requirements.txt)
- geopandas
- shapely
- pandas
- numpy

Ensure that all of the above modules amd their dependancies have been installed into python before running the scripts.

### Script Overview and Descriptions

#### clean_data.py

Python script that cleans all input datasets and preps them for analysis. Currently adapted to test data will change significantly in the future. 

#### points_into_polygons.py
Python script that takes the cleaned datasets and analyses them for intersections and proximity after linking the address and building data together using a linking dataset (usually of surveyed parcels). Outputs a dataset of building footprints that contains the linkages.

#### parcel_less_points_into_polygons.py

Experimental script that tests a workflow for dealing with situations where linking data is not available. This methodology uses a incrimentally increasing series of buffers to determine the closest address point to a building footprint. Accuracy yet to be determined.


### Environment Variables

Scripts utilize python-dotenv to carry environment variables between scirpts. The given layout below contains all key variables for the most recent version of the process. To
utilize this frame work fill in appropriate information in each of the variables below 


# Cleaned Data
CLEANED_BF_LYR_NAME = footprints_cleaned
CLEANED_AP_LYR_NAME = addresses_cleaned
CLEANED_RD_LYR_NAME = roads_cleaned
CLEANED_SP_LYR_NAME = parcels_cleaned
UNLINKED_BF_LYR_NME = unmatched_bfs
FLAGGED_AP_LYR_NME = ap_full
AP_CIVIC_ADDRESS_FIELD_NAME = NUMBER

# NB_INPUT_VARS
DATA_GPKG = 
OUTPUT_GPKG = 

CRS = 4269
PROJ_CRS = 2960
RD_CRS = 4617

LINKING_PATH = 
LINKING_LYR_NME = 'pan_ncb'

BF_PATH = 
# BF_PATH = 
# BF_LYR_NME = 

ADDRESS_PATH = 
ADDRESS_LAYER = 

ADDRESS_TYPE_CODES = 

AOI_MASK = 

LINKED_BY_DATA_NME = fredericton_inter_linked_merged
LINKED_BY_BUFFER_NME = via_buffer_linkage
UNLINKED_NME = non_geolinked

MATCHED_OUTPUT_GPKG = 

METRICS_CSV_OUT_PATH = 

AP_CASES_GPKG = 

MATCH_ACC_GPKG = 

BP_THRESHOLD = 20

