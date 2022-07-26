import requests
import sys, os
import pandas as pd
import geopandas as gpd
import shutil
from bs4 import BeautifulSoup
import zipfile
import io


'''
Purpose of this script is to scrape and download all fgdbs from the NRCan autobuildings site and get a count for all the records in the file
'''

# -------------------------------------------------------------------------------------------
# Funtions

# -------------------------------------------------------------------------------------------
# Inputs

source_link = 'https://ftp.maps.canada.ca/pub/nrcan_rncan/extraction/auto_building/fgdb/'
out_folder = r'C:\projects\point_in_polygon\data\nrcan_bldgs'
# -------------------------------------------------------------------------------------------
# Logic

reqs = requests.get(source_link)

soup = BeautifulSoup(reqs.text, 'lxml')

# compile all urls from the site
urls = []
for a in soup.find_all('a', href=True):
    if a.get('href').split('.')[-1] == 'zip':
        ziplink = a.get('href')
        full_link = f'{source_link}{ziplink}'
        urls.append(full_link)

# download the files to the given out folder
for u in urls:
    print(f'Downloading and Extracting: {u}')
    with requests.get(u) as r:
        z= zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(out_folder)

print('DONE!')
