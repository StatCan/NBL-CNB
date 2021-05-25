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


