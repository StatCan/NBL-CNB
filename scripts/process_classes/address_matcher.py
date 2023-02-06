import geopandas as gpd
import pandas as pd
import sys
import os

# Process Class Imports
from issue_flagging_class import IssueFlagging
from matching_master_class import Matcher
from qa_qc_classes import MatchQaQC


class AddressMatcher:

    def __init__(self, add_pts, bld_polys, pcl_fbc, add_pts_lyr_nme = None, bld_polys_lyr_nme = None, pcl_fbcs_lyr_nme= None, aoi = None, aoi_lyr_nme=None) -> None:
        
        self.bp = gpd.read_file(bld_polys, mask=aoi)
        self.adp = gpd.read_file(add_pts, layer= add_pts_lyr_nme, mask=aoi)
        self.pcl = gpd.read_file(pcl_fbc, layer=pcl_fbcs_lyr_nme, mask=aoi)
    
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        
        # On call run each process class in order

        # Step 1: Data Cleaning

        # Step 2: Parcel Relationship Calculation

        #etc

def main():
    pass

if __name__ == "__main__":
    main()
    print('DONE!')