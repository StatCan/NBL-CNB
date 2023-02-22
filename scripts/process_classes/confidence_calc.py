import datetime
import os
import sys
import fiona
from dotenv import load_dotenv
from pathlib import Path
import geopandas as gpd
from matplotlib.pyplot import axis
import numpy as np
import pandas as pd
import click

class ConfidenceCalculator():
    '''Calculates the confidence of any given matches based off of various match charateristics and secondary sources'''
    
    def __init__(self, matched_adp, parcels_gdf, lines_gdf, proj_crs, civic_data_gpkg=None, civic_data_lyr_nme=None) -> None:
        
        self.addresses = matched_adp
        self.parcels_gdf = parcels_gdf
        self.civic_data_gpkg = civic_data_gpkg
        self.civic_data_lyr_nme = civic_data_lyr_nme
        self.lines_gdf = lines_gdf

        self.proj_crs = proj_crs

        self.confidence_vars = ['parcel_rel', 'mun_civic_flag', 'parcel_loc_flag', 'link_length', 'method', 'nar_link_flag', 'sbgr_link_flag']
    

    def __call__(self) -> None:

        # Create flags for secondary address sources
        if self.civic_data_gpkg == None:
            click.echo('No municipal civics data available')
            self.addresses['mun_civic_flag'] = np.NaN
        else:
            mun_civics = gpd.read_file(self.mun_civic_gpkg, layer=self.mun_civic_lyr_nme, crs=proj_crs, driver='GPKG')
            click.echo('Prepping municipal civic fields')
            mun_civics['st_nme'] = mun_civics['st_nme'].str.upper().str.replace(' ', '')
            click.echo('Creating municipal civics flag')
            self.addresses['mun_civic_flag'] = self.addresses[['link_field', 'number', 'street', 'stype_en']].apply(lambda row: self._civics_flag_builder(row[1],row[2],row[3],mun_civics[mun_civics['link_field'] == row[0]]), axis=1) 

        click.echo('Creating parcel location field flags')
        #self.addresses['parcel_loc_flag'] = addresses[['link_field', 'number', 'street', 'stype_en']].apply(lambda row: parcel_location_flag_builder(row, parcels[parcels['link_field'] == row[0]][['link_field', 'address_min', 'address_max', 'street_name', 'street_type']]), axis=1)
        self.addresses['parcel_loc_flag'] = np.NaN

        if 'nar_addr_guid' in self.addresses.columns.tolist():
            click.echo('Creating NAR linkage flag')
            self.addresses['nar_link_flag'] = self.addresses['nar_addr_guid'].apply(lambda x: 1 if type(x) == str else 0)

        else:
            click.echo('No NAR linkage available to check')
            self.addresses['nar_link_flag'] = np.NaN

        if 'sbgr_bg_sn' in self.addresses.columns.tolist():
            click.echo('Creating SBgR SN linkage flag')
            self.addresses['sbgr_link_flag'] = self.addresses['sbgr_bg_sn'].apply(lambda x: 1 if type(x) == str else 0)

        else:
            click.echo('No SBgR SN linkage available to check')
            self.addresses['sbgr_link_flag'] = np.NaN

        # Calculate confidence score and associated fields
        click.echo('Calculating Confidence')

        self.addresses['confidence'] = self.addresses[self.confidence_vars].apply(lambda row: self._confidence_score_calculator(*row), axis=1)

        self.addresses['con_valid_inputs'] = self.addresses[self.confidence_vars[1:]].apply(lambda row: self._valid_confidence_input_counter(*row), axis=1)
        self.addresses['con_total_inputs'] = self.addresses[self.confidence_vars[1:]].apply(lambda row: self._total_confidence_input_counter(*row), axis=1)

        self.addresses['confidence_type'] = self.addresses['confidence'].apply(lambda c: self._determine_confidence_type(c))

        # Add confidence to line links
        self.lines_gdf = self.lines_gdf.merge(self.addresses[['link_id', 'confidence', 'confidence_type']], on='link_id')


    def data_export():
        '''method to export the data after processing is complete'''


    def _confidence_score_calculator(self, parcel_rel, mun_civ_flag, parcel_loc_flag, link_len, method, nar_link, sbgr_link) -> int:
        '''Returns a match confidence score based on key fields calculated during the matching process. Use only as part of an apply function on a single record'''
        parcel_rel_scores = {'one_to_one' : 60,
                            'one_to_many' : 55, 
                            'many_to_one' : 50, 
                            'many_to_many' : 40, 
                            'unlinked' : 30, 
                            'manual' : 100,
                            'other' : 0}
        
        method_scores = {
            'intersect' : 7,
            'data_linking' : 3,
            '20m_buffer' : 0,
            '20m_buffer_bp' : 0
        }

        confidence = 0

        # initial calculation based on the parcel relationship
        if parcel_rel in parcel_rel_scores:
            confidence += parcel_rel_scores[parcel_rel]
        else:
            confidence += parcel_rel_scores['other']
        
        # MODIFIER #1: Secondary Address Sources (municipal civic, NAR, parcel location)
        if mun_civ_flag == 1:
            confidence += 5
        # Commented out until new solution is found
        # if parcel_loc_flag == 1:
        #     confidence += 5

        # MODIFIER #2 Link Distance 
        if link_len <= 5:
            confidence += 10
        if (link_len > 5) and (link_len <= 20):
            confidence += 5
        if (link_len > 20) and (link_len <= 50):
            confidence += 1
        if (link_len > 50) and (link_len <= 200): # Here just to visualize the category. Doesn't change score
            confidence += 0
        if (link_len > 200) and (link_len <= 400): # Score reduction starts here
            confidence -= 10
        
        # MODIFIER #3: NAR and SBgR Linkages
        if nar_link == 1:
            confidence += 10
        if sbgr_link == 1:
            confidence += 5

        # MODIFIER #4: Link Method
        if method in method_scores:
            confidence += method_scores[method]
        else:
            confidence += 0

        return confidence


    def _valid_confidence_input_counter(self, mun_civ_flag, parcel_loc_flag, link_len, method, nar_link, sbgr_link):
        '''Returns the number of valid modifiers on the parcel relationship score that were used to help calculate the confidence value. 
        Parcel relationship is not included in this calculation.'''

        v_score = 0 
        # For preflagged modifiers check for the match flag
        for mod in [mun_civ_flag, nar_link, sbgr_link]: #parcel_loc_flag]:
            if mod == 1:
                v_score += 1
        
        # Specific checks for other flags
        
        # For link len check that the link len is within the lowest positive scoring distance (<50)
        if link_len < 50:
            v_score +=1
        
        # For method add only methods that contribute to a positive score
        if method in ['intersect', 'data_linking']:
            v_score +=1
        # Add other specific modifiers here if they become available
        
        return v_score


    def _total_confidence_input_counter(self, mun_civ_flag, parcel_loc_flag, link_len, method, nar_link, sbgr_link):
        '''Returns the total number of confidence modifiers that had a valid input (
            modifiers with an invalid input -1 or NULL are excluded from this calculation)'''
        
        i_score = 0 
        
        # For preflagged modifiers check if the record doesn't equal the invalid flag
        for mod in [mun_civ_flag, nar_link, sbgr_link]:# parcel_loc_flag]:
            if mod != -1:
                i_score += 1
        # If score is between 0 and 50 take as a positive indicator (50 being the lowest positive category)
        if (link_len >= 0.0) and (link_len <= 50.0):
            i_score +=1
        
        if type(method) == str:
            i_score += 1
        
        return i_score


    def _determine_confidence_type(self, con_score):
        '''Returns a string denoting the level of confidence in the match based on the integer value of a given input field (usually 'confidence')'''

        if con_score >= 70:
            return 'HIGH'
        if (con_score >= 60) and (con_score < 70):
            return 'MEDIUM'
        else:
            return 'LOW'


@click.command()
@click.argument('env_path', type=click.STRING)
def main(env_path:str) -> None:

    load_dotenv(env_path)

    output_path = os.getcwd()
    match_gpkg = os.getenv('MATCHED_OUTPUT_GPKG')
    match_lyr_nme = os.getenv('MATCHED_OUTPUT_LYR_NME')

    project_gpkg = Path(os.getenv('DATA_GPKG'))
    footprints_lyr_nme = os.getenv('CLEANED_BF_LYR_NAME')
    parcel_lyr_nme = 'parcels_cleaned'

    qa_qc_gpkg = Path(os.getenv('QA_GPKG'))
    addresses_lyr_nme = 'qc_points'
    line_link_lyr_nme = f"line_links"

    mun_civic_gpkg = Path(os.getenv('QA_GPKG'))
    mun_civic_lyr_nme = os.getenv('ST_MUN_CIVICS')

    proj_crs = os.getenv('PROJ_CRS')

    matched_gdf = gpd.read_file(qa_qc_gpkg, layer=addresses_lyr_nme, crs=proj_crs)
    parcels_gdf = gpd.read_file(project_gpkg, layer=parcel_lyr_nme, crs=proj_crs)
    lines_gdf = gpd.read_file(qa_qc_gpkg, layer=line_link_lyr_nme, crs=proj_crs)

    confidence = ConfidenceCalculator(matched_gdf, parcels_gdf, lines_gdf, proj_crs)
    confidence()

    click.echo('DONE!')

if __name__ == '__main__':
    main()



    


