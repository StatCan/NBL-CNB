import os, sys
import pandas as pd
import numpy as np
import geopandas as gpd
from dotenv import load_dotenv
from pathlib import Path
from math import isnan
import shapely.speedups
import datetime
import swifter
import click
shapely.speedups.enable()
pd.options.mode.chained_assignment = None
'''
The purpose of this script is to highlight potentially problematic building footprints as they relate to associated parcel fabrics and building points.
Generates a report of counts based on known potentially problematic situations

Examples of potentially problematic situations include (examples with ✓ are those that have been added rest are planned):

Footprints:
- Footprint intersects with multiple parcels ✓
- Footprint contains many points with many unique addresses
- Footprint not within a parcel ✓
- Multiple footprints within one parcel

Points:
- Point not within parcel ✓
- Multipoint within one parcel ✓
- More points than buildings in a parcel ✓

'''

# -------------------------------------------------------
# Class

class IssueFlagging:
    '''
    The purpose of this class is to highlight the relationships between a parcels layer and a address point layer
    '''
    def __init__(self, ap_data: gpd.GeoDataFrame, bp_data:gpd.GeoDataFrame, crs):
       
        # Core data import
        self.addresses = ap_data
        self.footprints = bp_data

        self.proj_crs = crs    
    
    def __call__(self):

        self.footprints.to_crs(crs=self.proj_crs, inplace=True)
        self.addresses.to_crs(crs=self.proj_crs, inplace=True)
        
        # produce basic layers
        click.echo('Grouping APs')
        grouped_ap = self.addresses.groupby('link_field', dropna=True)['link_field'].count()
        click.echo('Grouping BFs')
        grouped_bf = self.footprints[self.footprints['shed_flag'] == False].groupby('link_field', dropna=True)['link_field'].count()
        click.echo('Determining Relationships')
        self.addresses['parcel_rel'] = self.addresses['link_field'].apply(lambda x: self._relationship_setter(x, grouped_ap, grouped_bf))


    def _relationship_setter(self, parcel_ident, ap_parcel_counts, bf_parcel_counts):
            '''Returns the parcel relationship type for the given record based on the counts of the parcel linkages in the bf and ap datasets'''
            from math import isnan
            if isnan(parcel_ident):
                return 'unlinked'
            bf_indexes = bf_parcel_counts.index.tolist()

            if not parcel_ident in bf_indexes:
                return 'no_linked_building'

            ap_count = ap_parcel_counts[ap_parcel_counts.index == parcel_ident].tolist()[0]
            bf_count = bf_parcel_counts[bf_parcel_counts.index == parcel_ident].tolist()[0]

            if (ap_count == 1) and (bf_count == 1):
                return 'one_to_one'

            if (ap_count == 1) and (bf_count > 1):
                return 'one_to_many'

            if (ap_count > 1) and (bf_count == 1):
                return 'many_to_one'

            if (ap_count > 1) and (bf_count > 1):
                return 'many_to_many'

            print(ap_count)
            print(bf_count)
            sys.exit()


    def export_results(self, out_path:str, out_lyr_name='ap_full'):
        '''outputs results to a given gpkg'''
        self.addresses.to_file(out_path, layer=out_lyr_name)
   
@click.command()
@click.argument('env_path', type=click.STRING)
@click.option("--out_name", default="ap_full", show_default=True, help="Name of output layer")
def main(env_path:str, out_name:str):
    '''
    Creates the parcel relationship field in the address points data set. Assumes the inputs have already been cleaned and linkages created.

    env_path: the path to the environments file containing the information needed to setup the data
    '''

    load_dotenv(env_path)

    bf_path =  Path(os.getenv('DATA_GPKG'))
    bf_lyr_nme = 'footprints_cleaned'
    
    ap_path = Path(os.getenv('DATA_GPKG'))
    ap_lyr_nme = 'addresses_cleaned'
    # ap_path = Path(os.getenv('ADDRESS_PATH'))
    # ap_lyr_nme = os.getenv('ADDRESS_LAYER')

    output_gpkg = Path(os.getenv('DATA_GPKG'))

    proj_crs = int(os.getenv('PROJ_CRS'))

    # AOI mask if necessary
    aoi_mask = os.getenv('AOI_MASK')
    
    if aoi_mask != None:
        aoi_mask = gpd.read_file(aoi_mask)

    # data gpkg creation
    ap = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_mask)
    bf = gpd.read_file(bf_path, layer=bf_lyr_nme, mask=aoi_mask)

    issues_flagged = IssueFlagging(ap, bf, crs=proj_crs)
    issues_flagged()
    click.echo('Exporting Results')
    issues_flagged.export_results(output_gpkg, out_name)
    click.echo('DONE!')
    
    
if __name__ == "__main__":
    main()

