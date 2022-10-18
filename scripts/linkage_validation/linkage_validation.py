import string
import click
import fiona
import shapely
import geopandas as gpd
import numpy as np
import logging
import libpysal
import pandas as pd
import sys, os
from copy import deepcopy
from itertools import chain, count
from operator import attrgetter, itemgetter
from pathlib import Path
from shapely.geometry import Point
from shapely.ops import polygonize, unary_union

'''

For the purposes of highlighting the manual workflow. This script should run as a command line tool for a manual editor
to run on a specific subset of polygon geometry. This tool will then return all records that need manual validation in
the AOI

Based off of the CRN validation script but with significant simplifications (link below to original)

https://github.com/StatCan/egp-crn/blob/master/src/meshblock/validate_meshblock.py
https://github.com/StatCan/egp-crn/blob/master/src/conflation/conflate_meshblock.py
https://james-brennan.github.io/posts/fast_gridding_geopandas/

- Create grid programatically or manually
- Select one subset of the cells or subdivide of necessary
- Flag issues for review

'''

# ----------------------------------------------------------------
# Functions

def basic_grid(layer_of_interest: gpd.GeoDataFrame, grid_crs: int = 4326, n_cells: int = 10) -> gpd.GeoDataFrame:
    '''
    Creates a basic grid based of the extent of the input layer of interest. n_cells is the number of desired cells on one axis although if the extent is odd then
    the desired number of cells will not be exact.
    '''
    # Calc size of cells
    xmin, ymin, xmax, ymax = layer_of_interest.total_bounds
    cell_size = (xmax - xmin) / n_cells

    grid_cells = []
    for x0 in np.arange(xmin, xmax + cell_size, cell_size):
        for y0 in np.arange(ymin, ymax + cell_size, cell_size):
            # bounds
            x1 = x0 - cell_size
            y1 = y0 + cell_size
            grid_cells.append(shapely.geometry.box(x0, y0, x1, y1))
    return gpd.GeoDataFrame(grid_cells, columns=['geometry'], crs=grid_crs)

def dissolved_parcel_grid(parcels: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    '''
    Dissolves boundaries between parcel and returns pseudo basic block which cna then be used for ananlysis. To prevent the return of a single giant polygon ensure that
    all road polygons are deleted before running this function. Road parcels can often be distinguished in the lot_number field in parcel data (if available) 
    '''    
    # create spatial weights matrix
    matrix = libpysal.weights.Queen.from_dataframe(parcels)
    
    # get component labels
    comps = matrix.component_labels

    return parcels.dissolve(by=comps)

# ----------------------------------------------------------------
# Inputs

matched_points_gpkg = r'C:/projects/point_in_polygon/data/NT_data/qa_qc_files.gpkg'
points_lyr_nme = 'matches_w_confidence'
par_adj_gpkg = r'C:\projects\point_in_polygon\data\NT_data\grid_test.gpkg'
par_adj_lyr_nme = 'parcels_adjusted'
out_dir = r'C:/projects/point_in_polygon/data/NT_data'
out_gpkg = r'C:/projects/point_in_polygon/data/NT_data/NWT_grid_test.gpkg'
out_lyr_nme = 'grid_test'
out_csv_name = 'aoi_priorities.csv'
NWT_crs = 26911

# ----------------------------------------------------------------
# Logic

# Load in the inputs
matched_gdf = gpd.read_file(matched_points_gpkg, layer=points_lyr_nme)
par_adj_gdf = gpd.read_file(par_adj_gpkg, layer=par_adj_lyr_nme)

# Check and set the crs for the inputs
for gdf in [par_adj_gdf, matched_gdf]:
    if gdf.crs != NWT_crs:
        gdf.to_crs(NWT_crs, inplace=True)

# Create dissolved parcel grid
combo_polys = dissolved_parcel_grid(par_adj_gdf)

# Create a unique block ID for each block
combo_polys['block_id'] = combo_polys.index

# Create spatial join to get the block_id for the matches
matched_gdf = matched_gdf.sjoin(combo_polys[['block_id', 'geometry']])
matched_gdf.drop(columns=['index_right'], inplace=True)

# Group and get counts
grouped_w_par = matched_gdf.groupby(by=['block_id'])
con_type_cnts = grouped_w_par['confidence_type'].value_counts()

# Convert the series to a dataframe
counts_df = con_type_cnts.to_frame('confidence_type').unstack(fill_value=0, level=-1)
# Get rid of the multi index
counts_df.columns=counts_df.columns.droplevel(0)
counts_df.reset_index(inplace=True)
# Better column order
counts_df = counts_df[['block_id', 'LOW', 'MEDIUM', 'HIGH']]
# Calc total # records in the block
counts_df['total'] = counts_df['HIGH'] + counts_df['MEDIUM'] + counts_df['LOW']
# Sort largest totals to the top of the table
counts_df.sort_values(by='total', inplace=True, ascending=False)
# Set the block_id as the index
counts_df.set_index('block_id', inplace=True)

# Create Priority Field
counts_df['percent_to_check'] = round(((counts_df['MEDIUM'] + counts_df['LOW'])/ counts_df['total']) * 100, 2)

counts_df.to_csv(os.path.join(out_dir, out_csv_name))
print('DONE!')
