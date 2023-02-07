import geopandas as gpd
import pandas as pd
import sys
import os

# Process Class Imports
from data_cleaning import CleanData
from issue_flagging_class import IssueFlagging
from matching_master_class import Matcher
from qa_qc_classes import MatchQaQC


class AddressMatcher:
    '''
    Compiles the address matching process into a single file for ease of use. If running the process one step at a time please use the classes in their original files.
    '''

    def __init__(self, add_pts, bld_polys, pcl_fbc, add_pts_lyr_nme = None, bld_polys_lyr_nme = None, pcl_fbcs_lyr_nme= None, aoi = None, aoi_lyr_nme=None) -> None:
        
        self.bp = gpd.read_file(bld_polys, mask=aoi)
        self.adp = gpd.read_file(add_pts, layer= add_pts_lyr_nme, mask=aoi)
        self.pcl = gpd.read_file(pcl_fbc, layer=pcl_fbcs_lyr_nme, mask=aoi)

        # set crs (hardcoded for now)
        self.geo_crs = 4326
        self.proj_crs = 2960

        
    def __call__(self):
        
        # On call run each process class in order
        # Step 1: Data Cleaning
        clean = CleanData(self.adp, self.bp, self.pcl)
        # Step 2: Parcel Relationship Calculation
        flagged = IssueFlagging(clean.adp, clean.bp, clean.parcels, crs= self.proj_crs)
        # Step 3: Matching 
        matched = AddressMatcher(flagged.addresses, clean.bp, clean.parcels)
        # Step 4: QA/QC
        qa_qc = MatchQaQC()
        # Step 5: Confidence Calculation
        
    def export_data(export_directory: str):
        '''Creates a geopackage at the given directory with all outputs'''
        # Key output vars
        out_gpkg_pth = os.path.join(export_directory, 'match_results')


def main():
    pass

if __name__ == "__main__":
    main()
    print('DONE!')