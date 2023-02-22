import os
import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
sys.path.insert(1, os.path.join(sys.path[0], ".."))
from shapely.geometry import LineString, Point
from dotenv import load_dotenv
import datetime
import click
pd.options.mode.chained_assignment = None
class MatchQaQC:
    def __init__(self, matched_points, orig_points, proj_crs=4326, max_link_distance:int=450) -> None:

       self.match_adp = matched_points
       self.clean_adp = orig_points
       self.proj_crs = proj_crs
       self.max_link_distance = max_link_distance 


    def __call__(self):
        
        self.match_adp.to_crs(crs=self.proj_crs, inplace=True)
        self.clean_adp.to_crs(crs=self.proj_crs, inplace=True)

        # Match unique id creation
        self.match_adp['link_id'] = range(1, len(self.match_adp.index)+1)

        self.match_adp['line_geom'] = self.match_adp[['a_id', 'geometry']].apply(lambda row: self._line_link_maker(row[1], self.clean_adp[self.clean_adp['a_id'] == row[0]]['geometry'].tolist()[0]), axis=1)

        self.match_adp = self.match_adp.set_geometry('line_geom')

        self.match_adp.rename(columns={'geometry': 'point_geometry'}, inplace=True)
        self.match_adp.rename(columns={'line_geom':'geometry'}, inplace=True)
        self.match_adp= self.match_adp.set_geometry('geometry')

        # Filter out those links that exceed the maximum limit for linkage distance
        self.match_adp['link_length'] = self.match_adp['geometry'].apply(lambda l: round(l.length, 2))

        click.echo('Filtering out long links')
        # Filter out records that are greater than the maximum acceptable link length
        self.long_links = self.match_adp.loc[self.match_adp['link_length'] > self.max_link_distance]
        click.echo(f'Isolating: {len(self.long_links)} long links')
        if len(self.long_links) > 0:
            self.long_lines = self.long_links.copy(deep=True)
            self.long_lines.drop(columns=['point_geometry'], inplace=True)
            self.long_links.drop(columns=['geometry'], inplace=True)
            self.long_links.rename(columns={'point_geometry':'geometry'}, inplace=True)
            self.long_links = self.long_links.set_geometry('geometry')

            # filter out records that are above the link threshold 
            self.match_adp = self.match_adp[~self.match_adp.index.isin((self.long_links.index))]

        # Output line file to the qa_qc gpkg
        self.line_links = self.match_adp.copy(deep=True)
        self.line_links.drop(columns=['point_geometry'], inplace=True)

        self.match_adp.drop(columns=['geometry'], inplace=True)
        self.match_adp.rename(columns={'point_geometry':'geometry'}, inplace=True)
        self.match_adp = self.match_adp.set_geometry('geometry')
        self.match_adp.to_crs(crs=self.proj_crs, inplace=True)

    def _line_link_maker(self, matched_geometry:Point, orig_geometry:Point) -> LineString:
            '''
            Creates lines for illustrating the matches made during matching_master.py takes the matched point geometry and the original point geometry and returns a line 
            with those as the start and end points. 
            '''
            line_obj = LineString([orig_geometry, matched_geometry])
            return line_obj


    def export_outputs(self, out_gpkg, line_links_lyr_nme='line_links', match_adp_lyr_nme='qc_points', long_link_point_lyr_nme='long_links', out_crs:int=4326):
        self.match_adp.to_file(out_gpkg, layer=match_adp_lyr_nme, crs=out_crs)
        self.line_links.to_file(out_gpkg, layer=line_links_lyr_nme, crs=out_crs)
        if len(self.long_links) > 0:
            self.long_links.to_file(out_gpkg, layer=long_link_point_lyr_nme, driver='GPKG', crs=out_crs)


@click.command()
@click.argument('env_path', type=click.STRING)
def main(env_path:str):
    click.echo('Starting Process')
    load_dotenv(env_path)

    output_path = os.getcwd()

    proj_crs = int(os.getenv('PROJ_CRS'))

    matched_points_path = Path(os.getenv('MATCHED_OUTPUT_GPKG'))
    matched_points_lyr_nme = 'point_linkages'

    long_link_point_lyr_nme = 'long_points'
    long_link_line_lyr_nme = 'long_lines'

    project_gpkg = Path(os.getenv('DATA_GPKG'))
    addresses_lyr_nme = os.getenv('FLAGGED_AP_LYR_NME')

    qa_qc_gpkg = Path(os.getenv('QA_GPKG'))

    matched_gdf = gpd.read_file(matched_points_path, layer= matched_points_lyr_nme, crs=proj_crs)
    clean_adp = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs)

    matched = MatchQaQC(matched_gdf, clean_adp, proj_crs=proj_crs)
    matched()
    click.echo('DONE!')

if __name__ == '__main__':
    main()
    