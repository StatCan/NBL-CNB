import zipfile
import glob, os

'''
Utility script. Take a directory find all zip files and extract all files to another directory.
'''

dir_path = "C:\\projects\\point_in_polygon\\data\\bing_buildings\\zip"
extract_to = "C:\\projects\\point_in_polygon\\data\\bing_buildings"

os.chdir(dir_path)
zip_files = []
for file in glob.glob("*.zip"):
    zip_files.append(os.path.join(dir_path, file))

for z in zip_files:
     print(f'Extracting: {z}')
     with zipfile.ZipFile(z, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

print('DONE!')
