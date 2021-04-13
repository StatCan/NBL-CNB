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

ensure that all of the above modules have been installed into python before running the scripts
