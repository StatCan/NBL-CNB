import zipfile
import glob
import os
import sys

'''
Utility script. Take a directory find all zip files and extract all files to another directory.
'''

dir_path = r"Z:\working\NU_data\zips"
extract_to = r"Z:\working\NU_data\extracted"

os.chdir(dir_path)
zip_files = []
for file in glob.glob("*.zip"):
    zip_files.append(os.path.join(dir_path, file))

for z in zip_files:
     print(f'Extracting: {z}')
     f_name = (os.path.split(z)[-1]).split('.')[0]
     if f_name.split('_')[-1] == 'parcels':
         f_file = 'parcels'
     if f_name.split('_')[-1] == 'footprints':
         f_file = 'footprints'
     with zipfile.ZipFile(z, 'r') as zip_ref:
        zip_ref.extractall(os.path.join(extract_to, f_file, f_name))

print('DONE!')
