Step 4: Match QA/QC
===================

.. toctree::
    :maxdepth: 2
    :hidden:

Once the matching is complete some Quality Assessment (QA) and Quality Control (QC) is performed.
Some data products are also produced to aid in manual assessment of the matches.

Line Links
----------

The first product that is produed at this stage of the process is the creation of a line dataset
that starts at the address point and ends at the representative point of the building it is matched to. 
This makes it easy to visually distinguish the number and quality of matches associated with any given
address point or building. These lines also serve to highlight areas where potential matches have been 
missed by the matching process. 

Long Links
----------

Once the line links have been created their length can be assessed. In general the larger the distance 
between the address point and the building the less likely the match is to be correct.
Through analysis of test data an upper threshold of 450m was set for matches. All matches with a distance
greater than 450m are removed and exported in a layer called long_links for further analysis.

Other QA/QC
-----------

To be added as needed 

