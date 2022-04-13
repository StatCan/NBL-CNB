# points_to_polygons_PoC

## Description and Sources
Proof of concept for matching address points to building footprints. As an initial prototype  New Brunswick was chosen. 

All data for this project downloaded from the geonb data portal a link to which can be found here:
http://www.snb.ca/geonb1/e/DC/catalogue-E.asp

Note that since some of the data is continuously updated on geonb there may be differences in certain results depending on the vintage of the data. 

### Layers Used (as they appear on geonb):
- Address New Brunswick Civic Address Database (Address NB)
- New Brunswick Buildings
- Property Assessment Map

### This project was built in python using the following key modules (a full list can be found in the requirements.txt)
Note that since this project is still in developments these requirements are subject to change.

- geopandas
- shapely
- pandas
- numpy

Ensure that all of the above modules and their dependancies have been installed into python before running the scripts.

### Script Overview and Descriptions

#### clean_data.py

Python script that cleans all input datasets and preps them for analysis. Currently needs to be adapted on a province by province basis due to data availablity. There will be
significant differences between versions. clean_data.py is the baseline version of the script to find the province specific version look for the file with the following naming
convention "*provincial abbreviation*_clean_data.py" with provincial abbreviation being the abbreviation of the specific province. For example, the cleaning script for New
Brunswick would be named "NB_clean_data.py"

#### issue_flagging.py
Python script that takes the cleaned datasets and calculates some basic metrics as well as determining the relationship between the address points and building footprints in the
parcel.

#### matching_master.py

This script creates the matches between the address points and the building footprints. All basic methods and subclasses are contained within this script. Outputs a point layer
with the link value in the 'footprint_index' field 

#### qa_qc.py

This script produces data products that are useful for performing QA and QC on the data. Currently the only product produced is a layer that draws a line between the address point and the building centroid that it is matched with. There is the potential for more products to be added here in the future.

### Environment Variables

The scripts utilize python-dotenv to carry environment variables between scirpts. The given layout below contains all key variables for the most recent version of the process. To utilize this frame work fill in appropriate information in each of the variables below (before use comment out or remove explanitory comments) 

#### Environment Variables

CLEANED_BF_LYR_NAME = footprints_cleaned
CLEANED_AP_LYR_NAME = addresses_cleaned
CLEANED_RD_LYR_NAME = roads_cleaned
CLEANED_SP_LYR_NAME = parcels_cleaned
UNLINKED_BF_LYR_NME = unmatched_bfs
FLAGGED_AP_LYR_NME = ap_full
AP_CIVIC_ADDRESS_FIELD_NAME = NUMBER        The field in the address points data where the civic number is kept 

DATA_GPKG = 
OUTPUT_GPKG = 

PROJ_CRS = 2960            Projection for the process (example given was used for Fredericton matching)

LINKING_PATH =             Path to parcel data
LINKING_LYR_NME =          Layer Name (if applicable depending on file type)

BF_PATH =                  Path to building footprint data
BF_LYR_NME =               Layer Name (if applicable depending on file type)

ADDRESS_PATH =             Path to address point data data
ADDRESS_LAYER =            Layer Name (if applicable depending on file type)

ADDRESS_TYPE_CODES = 

AOI_MASK =                 Optional Input: Path to an area of interest polygon file that will be used to clip the input data to the AOI

LINKED_BY_DATA_NME = fredericton_inter_linked_merged
LINKED_BY_BUFFER_NME = via_buffer_linkage
UNLINKED_NME = non_geolinked

MATCHED_OUTPUT_GPKG =       Input path to a geopackage here (can be new)

METRICS_CSV_OUT_PATH =      Input path to a geopackage here (can be new)

AP_CASES_GPKG =             Input path to a geopackage here (can be new)

MATCH_ACC_GPKG =            Input path to a geopackage here (can be new)

BP_THRESHOLD = 20           Input path to a geopackage here (can be new)
