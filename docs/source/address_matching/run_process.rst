How to run the Matching Process
===============================

.. toctree::
   :maxdepth: 2
   :hidden:

Setup
-----

In order to run the matching process a python 3 environment is required with the following packages (as well as their dependancies) installed:

* Pandas
* GDAL
* Shapely
* Fiona
* Geopandas
* python-dotenv
* pathlib

It is reccomended to start with a fresh venv and install the modules using the conda-forge channel on anaconda for the smoothest installation 
experience. The requirement.txt file found in the github repository will allow for a streamlined method to setup the environment. Running an install 
of the requirements.txt would be as follows:

In order to run the process effectively an environments file needs to be created. This file will contain the key information that the process
needs to run. The environments file should be made up of the following variables (this list may vary based on data availability. Key variables are bolded for emphasis):

.. code-block:: markdown
   
   CLEANED_BF_LYR_NAME = footprints_cleaned
   CLEANED_AP_LYR_NAME = addresses_cleaned
   CLEANED_RD_LYR_NAME = roads_cleaned
   CLEANED_SP_LYR_NAME = parcels_cleaned
   UNLINKED_BF_LYR_NME = unmatched_bfs
   FLAGGED_AP_LYR_NME = ap_full
   AP_CIVIC_ADDRESS_FIELD_NAME = NUMBER

   BASE_PATH = Z:\working\NWT_data

   DATA_GPKG = ${BASE_PATH}\working\data.gpkg
   OUTPUT_GPKG = C${BASE_PATH}\working\output.gpkg

   PROJ_CRS = 26911

   LINKING_PATH = ${BASE_PATH}\merged_parcels.gpkg
   LINKING_LYR_NME = merged_parcels

   BF_PATH = ${BASE_PATH}\ATLAS_extract.gdb
   BF_LYR_NME = Building_Footprints

   ADDRESS_PATH = ${BASE_PATH}\yk_ap.gdb
   ADDRESS_LAYER = yk_Address_Points

   SBGR_LINKS = 

   AOI_MASK = ${BASE_PATH}\yk_Municipal_Boundary_gdb.gdb
   AOI_LYR_NME = yk_municipal_boundary

   LINKED_BY_DATA_NME = fredericton_inter_linked_merged
   LINKED_BY_BUFFER_NME = via_buffer_linkage
   UNLINKED_NME = non_geolinked

   MATCHED_OUTPUT_GPKG =  ${BASE_PATH}\working\matched_output.gpkg
   MATCHED_OUTPUT_LYR_NME = point_linkages
   UNMATCHED_OUTPUT_LYR_NME = unlinked_points
   UNMATCHED_POLY_LYR_NME = unlinked_polygons

   MATCH_ACC_GPKG = ${BASE_PATH}\working

   BP_THRESHOLD = 10
   BP_AREA_THRESHOLD = 175

   QA_GPKG = ${BASE_PATH}\qa_qc_files.gpkg
   ST_MUN_CIVICS = clean_mun_civs

   FLAGGED_ADP_LYR_NME = flagged_adp

Initiate Process
----------------

Once setup is complete the address matching process can be intiated. To do this
