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
    def __init__(self, ap_data_path, bf_data_path, linking_data_path, ap_lyr_nme=None, bf_lyr_nme=None, linking_lyr_nme=None, aoi_mask=None, crs= 4326):
        def relationship_setter(parcel_ident, ap_parcel_counts, bf_parcel_counts):
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

        
        if aoi_mask != None:
            self.aoi_gdf = gpd.read_file(aoi_mask)
        else: self.aoi_gdf = None

        self.addresses = gpd.read_file(ap_data_path, layer=ap_lyr_nme, mask=self.aoi_gdf)
        footprints = gpd.read_file(bf_data_path, layer=bf_lyr_nme, mask=self.aoi_gdf)
        parcels = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=self.aoi_gdf)
        footprints.to_crs(crs=proj_crs, inplace=True)
        parcels.to_crs(crs=proj_crs, inplace=True)
        self.addresses.to_crs(crs=proj_crs, inplace=True)

        # produce basic layers
        print('Grouping APs')
        grouped_ap = self.addresses.groupby('link_field', dropna=True)['link_field'].count()
        print('Grouping BFs')
        grouped_bf = footprints[footprints['shed_flag'] == False].groupby('link_field', dropna=True)['link_field'].count()
        print('Determining Relationships')
        self.addresses['parcel_rel'] = self.addresses['link_field'].apply(lambda x: relationship_setter(x, grouped_ap, grouped_bf))

    def export_results(self, out_path:str, out_lyr_name='ap_full'):
        '''outputs results to '''
        self.addresses.to_file(out_path, layer=out_lyr_name)
   
# -------------------------------------------------------
# Inputs

load_dotenv(os.path.join(r'C:\projects\point_in_polygon\scripts', 'NB_environments.env'))
bf_path =  Path(os.getenv('DATA_GPKG'))
bf_lyr_nme = 'footprints_cleaned'
# bf_lyr_nme = 'footprint_linkages'

ap_path = Path(os.getenv('DATA_GPKG'))
ap_lyr_nme = 'addresses_cleaned'
# ap_path = Path(os.getenv('ADDRESS_PATH'))
# ap_lyr_nme = os.getenv('ADDRESS_LAYER')

linking_data_path = Path(os.getenv('DATA_GPKG'))
linking_lyr_nme = 'parcels_cleaned'

output_gpkg = Path(os.getenv('DATA_GPKG'))

proj_crs = int(os.getenv('PROJ_CRS'))

aoi_mask = os.getenv('AOI_MASK')

metrics_out_path = Path(os.getenv('METRICS_CSV_OUT_PATH'))

ap_cases_gpkg = Path(os.getenv('AP_CASES_GPKG'))

# -------------------------------------------------------

@click.command()
@click.argument()


def main():

    issues_flagged = IssueFlagging(ap_path, bf_path, linking_data_path, ap_lyr_nme, bf_lyr_nme, linking_lyr_nme, aoi_mask,crs=proj_crs)
    issues_flagged.export_results(output_gpkg, out_lyr_name='ap_full')
    
    
if __name__ == "__main__":
    main()
    print('DONE!')

 # Procedural version of the code to be kept incase of future need
    '''
    def as_int(val):
        "Step 4: Converts linkages to integer tuples, if possible"
        try:
            if isinstance(val, int):
                return val
            else:
                return int(val)
        except ValueError:
            return val

    def relationship_setter(parcel_ident, ap_parcel_counts, bf_parcel_counts):
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
    starttime = datetime.datetime.now()
    print(f'Start Time {starttime}')

    aoi_gdf = None
    if aoi_mask != None:
        aoi_gdf = gpd.read_file(aoi_mask)
    
    print('Loading in data')
    addresses = gpd.read_file(ap_path, layer=ap_lyr_nme, mask=aoi_gdf)
    footprints = gpd.read_file(bf_path, layer=bf_lyr_nme, mask=aoi_gdf)
    parcels = gpd.read_file(linking_data_path, layer=linking_lyr_nme, mask=aoi_gdf)
    footprints.to_crs(crs=proj_crs, inplace=True)
    parcels.to_crs(crs=proj_crs, inplace=True)
    addresses.to_crs(crs=proj_crs, inplace=True)

    print('Producing basic layers')
    # Add footprint and address relates by parcel 'groupby'
    print('Grouping APs')
    grouped_ap = addresses.groupby('link_field', dropna=True)['link_field'].count()
    print('Grouping BFs')
    grouped_bf = footprints[footprints['shed_flag'] == False].groupby('link_field', dropna=True)['link_field'].count()
    print('Determining relationship')
    addresses['parcel_rel'] = addresses['link_field'].parallel_apply(lambda x: relationship_setter(x, grouped_ap, grouped_bf))

    print('Creating and exporting metrics doc as spreadsheet')

    addresses.to_file(output_gpkg, layer='ap_full', driver='GPKG')
    # hour : minute : second : microsecond
    print(f'Total Runtime: {datetime.datetime.now() - starttime}')

    print('DONE!')'''
