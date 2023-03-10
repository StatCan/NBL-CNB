Run the Matching Process
========================

.. toctree::
   :maxdepth: 2
   :hidden:

Setup
-----

In order to run the matching process a python 3  environment is required with the following packages (as well as their dependancies) installed:

* Pandas
* GDAL
* Shapely
* Fiona
* Geopandas
* Swifter
* python-dotenv
* pathlib

It is reccomended to start with a fresh venv and install the modules using the conda-forge channel on anaconda for the smoothest installation 
experience. The requirement.txt file found in the github repository will allow for a streamlined method to setup the environment. Running an install 
of the requirements.txt would be as follows:

In order to run the process effectively an environments file needs to be created. This file will contain the key information that the process
needs to run. The environments file should be made up of the following variables (this list may vary based on data availability.):

.. code-block:: markdown
   
   # Varibles for cleaned layer names 
   CLEANED_BF_LYR_NAME = footprints_cleaned  
   CLEANED_AP_LYR_NAME = addresses_cleaned
   CLEANED_RD_LYR_NAME = roads_cleaned
   CLEANED_SP_LYR_NAME = parcels_cleaned
   UNLINKED_BF_LYR_NME = unmatched_bfs
   FLAGGED_AP_LYR_NME = ap_full
   
   # The layer name in for the civic address field in the civic address data
   AP_CIVIC_ADDRESS_FIELD_NAME = NUMBER

   # The root directory to which all data will be saved
   BASE_PATH = Z:\working\NWT_data

   # The path to the geopackage where the initial cleaned data will be saved
   DATA_GPKG = ${BASE_PATH}\working\data.gpkg

   # The path to the geopackage where the final output will be saved
   OUTPUT_GPKG = C${BASE_PATH}\working\output.gpkg

   # The CRS for the projection to be used for all layers must be projected
   PROJ_CRS = 26911
   
   # The initial path and layer name for the linking data (parcel data) 
   LINKING_PATH = ${BASE_PATH}\merged_parcels.gpkg
   LINKING_LYR_NME = merged_parcels

   # The initial path where the building polygon data is located
   BF_PATH = ${BASE_PATH}\ATLAS_extract.gdb
   BF_LYR_NME = Building_Footprints

   # The initial path to where the address point data is located
   ADDRESS_PATH = ${BASE_PATH}\yk_ap.gdb
   ADDRESS_LAYER = yk_Address_Points

   # If subsetting the data by a specific geographic region point these variables to the boundary file here
   AOI_MASK = ${BASE_PATH}\yk_Municipal_Boundary_gdb.gdb
   AOI_LYR_NME = yk_municipal_boundary


   MATCHED_OUTPUT_GPKG =  ${BASE_PATH}\working\matched_output.gpkg
   MATCHED_OUTPUT_LYR_NME = point_linkages
   UNMATCHED_OUTPUT_LYR_NME = unlinked_points
   UNMATCHED_POLY_LYR_NME = unlinked_polygons

   MATCH_ACC_GPKG = ${BASE_PATH}\working

   # variables for setting the thresholds used by the BP process at the mathcing stage
   BP_THRESHOLD = 10
   BP_AREA_THRESHOLD = 175

   QA_GPKG = ${BASE_PATH}\qa_qc_files.gpkg
   ST_MUN_CIVICS = clean_mun_civs

   FLAGGED_ADP_LYR_NME = flagged_adp

Initiate Process
----------------

Once setup above is complete the address matching process can be intiated. To do this we
will run the files from inside of the IDE of your choice.

1. Navigate to the scripts folder in the 
2. Ensure that the following line of code in 
