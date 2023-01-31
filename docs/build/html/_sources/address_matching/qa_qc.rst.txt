Step 4: Match QA/QC
===================

.. toctree::
    :maxdepth: 2
    :hidden:

For reference the descriptions on this page cover the code in **qa_qc.py**

Once the matching is complete some Quality Assessment (QA) and Quality Control (QC) is performed. Some data products are also produced to aid in manual assessment of the matches.
Future additions to this section are likely as issues are identified through manual editing.

Line Links
----------

The first product that is produed at this stage of the process is the creation of a line dataset
that starts at the address point and ends at the representative point of the building it is matched to. 
This makes it easy to visually distinguish the number and quality of matches associated with any given
address point or building. These lines also serve to highlight areas where potential matches have been 
missed by the matching process. 

The process for creating the line links is as follows:

1. Load the matched address points (output from the matching step) and the cleaned address points (output from the cleaning step) into geodataframes.
2. For each point in the matched address points extract matched point geometry and the original point geometry and use them as the start point and end point of the new shapely LineString object
3. Set the newly created LineString as the geometry.

.. code-block:: python
    
    def point_line_maker(matched_geometry, orig_geometry):
        '''
        Creates lines for illustrating the matches made during matching_master.py takes the matched point geometry and the original point geometry and returns a line 
        with those as the start and end points. 
        '''
        line_obj = LineString([orig_geometry, matched_geometry])
        return line_obj

    match_adp = gpd.read_file(matched_points_path, layer=matched_points_lyr_nme, crs=proj_crs)
    clean_adp = gpd.read_file(project_gpkg, layer=addresses_lyr_nme, crs=proj_crs)

    match_adp['line_geom'] = match_adp[['a_id', 'geometry']].apply(lambda row: point_line_maker(row[1], clean_adp[clean_adp['a_id'] == row[0]]['geometry'].tolist()[0]), axis=1)

Long Links
----------

Once the line links have been created their length can be assessed. In general the larger the distance 
between the address point and the building the less likely the match is to be correct.
Through analysis of test data an upper threshold of 450m was set for matches. All matches with a distance
greater than 450m are removed and exported in a layer called long_links for further analysis.

The process for filtering out the long links is as follows:

1. Calculate the length of the line created during the line link creation step.
2. Check to see if there are any linkages that are longer than the set maximum link distance (default is 450m).
3. If there is at least one long link export these records aside for further analysis and remove them from the main geodataframe.

.. code-block:: python
    
    match_adp['link_length'] = match_adp['geometry'].apply(lambda l: round(l.length, 2))

    # Filter out records that are greater than the maximum acceptable link length
    long_links = match_adp.loc[match_adp['link_length'] > max_link_distance]
    print(f'Exporting: {len(long_links)} long links')
    if len(long_links) > 0:
        long_lines = long_links.copy(deep=True)
        long_lines.drop(columns=['point_geometry'], inplace=True)
        long_lines.to_file(qa_qc_gpkg, layer=long_link_line_lyr_nme, driver='GPKG')

        long_links.drop(columns=['geometry'], inplace=True)
        long_links.rename(columns={'point_geometry':'geometry'}, inplace=True)
        long_links = long_links.set_geometry('geometry')

        long_links.to_file(qa_qc_gpkg, layer=long_link_point_lyr_nme, driver='GPKG', crs=proj_crs)

        # filter out records that are above the link threshold 
        match_adp = match_adp[~match_adp.index.isin((long_links.index))]


Other QA/QC
-----------

To be developed as needed.

