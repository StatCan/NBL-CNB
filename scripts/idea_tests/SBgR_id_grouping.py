import datetime
import os
import sys
from pathlib import Path
import geopandas as gpd
from matplotlib.pyplot import axis
import numpy as np
import pandas as pd

from dotenv import load_dotenv

'''
Test logic to see if address data can be grouped by SBgR ID's to discover which addresses can be grouped together in the same building

Test sbgr_bu_sn and sbgr_bg_sn To test if grouping on either of these is worthwhile

'''
# ----------------------------------------------------------------------------------------------------------------------------------------
# Inputs

load_dotenv(os.path.join(os.path.dirname(__file__), 'NB_environments.env'))
 
output_path = r'C:\projects\point_in_polygon\data'
qa_qc_gpkg = r'C:\projects\point_in_polygon\data\NB_data\data.gpkg'
addresses_lyr_nme = 'addresses_cleaned'

# ----------------------------------------------------------------------------------------------------------------------------------------
# Logic

# Load in data
addresses = gpd.read_file(qa_qc_gpkg, layer=addresses_lyr_nme, driver='GPKG')
print(f'Total Adresses: {len(addresses)}')
for f in ['sbgr_bg_sn', 'sbgr_bu_sn']:
    sbgr_gr = addresses.groupby(f, dropna=True)[f].count()
    subset = addresses[addresses[f].isin(sbgr_gr[sbgr_gr>1].index.tolist())]
    subset.to_file(os.path.join(output_path, 'sbgr_sn_tests.gpkg'), layer=f'{f}_test') 

print('DONE!')
