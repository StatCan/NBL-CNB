import click
import geopandas as gpd
import pandas as pd
import sys
import os
from dotenv import load_dotenv
from pathlib import Path

# Process Class Imports
from data_cleaning import CleanData
from issue_flagging_class import IssueFlagging
from matching_master_class import Matcher
from qa_qc_classes import MatchQaQC
from confidence_calc import ConfidenceCalculator

pd.options.mode.chained_assignment = None

class AddressMatcher:
    '''
    Compiles the address matching process into a single file for ease of use. If running the process one step at a time please use the classes in their original files.
    Input should be the path to an environments file containing the information needed to run the scripts
    '''

    def __init__(self, env_file_path: str) -> None:
        
        # load in environments
        load_dotenv(env_file_path)

        polygon_lyr = os.getenv('BF_PATH')
        polygon_lyr_name = os.getenv('BF_LYR_NME')

        ap_path = os.getenv('ADDRESS_PATH')
        ap_lyr_nme = os.getenv('ADDRESS_LAYER') 

        linking_path = os.getenv('LINKING_PATH')
        linking_lyr_nme = os.getenv('LINKING_LYR_NME')

        # Setup the aoi mask if available to filter the data on import
        aoi_mask = os.getenv('AOI_MASK')
        aoi = None
        if aoi_mask != None:
            aoi = gpd.read_file(aoi_mask)

        self.bp = gpd.read_file(polygon_lyr,layer=polygon_lyr_name, mask=aoi)
        self.adp = gpd.read_file(ap_path, layer= ap_lyr_nme, mask=aoi)
        self.pcl = gpd.read_file(linking_path, layer=linking_lyr_nme, mask=aoi)

        # set crs
        self.geo_crs = 4326
        self.proj_crs = os.getenv('PROJ_CRS')

        
    def __call__(self):
        
        # On call run each process class in order
        # Step 1: Data Cleaning
        clean = CleanData(self.adp, self.bp, self.pcl, self.proj_crs)
        clean()
        # Step 2: Parcel Relationship Calculation
        flagged = IssueFlagging(clean.adp, clean.bp, clean.parcels, crs= self.proj_crs)
        # Step 3: Matching 
        matched = Matcher(flagged.addresses, clean.bp, clean.parcels)
        # Step 4: QA/QC
        qa_qc = MatchQaQC(matched.out_gdf,)
        # Step 5: Confidence Calculation
        confident = ConfidenceCalculator()
        
    def export_data(export_directory: str) -> None: 

        '''Creates a geopackage at the given directory with all outputs'''
        
        # Key output vars
        out_gpkg_pth = os.path.join(export_directory, 'match_results')

@ click.command()
@ click.argument('env_path', type=click.STRING)
def main(env_path:str):
    
    # env_directory = os.path.join(os.path.dirname(__file__), 'NB_environments.env')
    matching = AddressMatcher(env_path)
    matching()
    matching.export_data()    
    

if __name__ == "__main__":
    main()
    print('DONE!')