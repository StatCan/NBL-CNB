Step 3: Matching
================

.. toctree::
   :maxdepth: 2
   :hidden:

The matching stage of the process is broken down into five steps

Step 1: Load Data and Configure Attributes
------------------------------------------


Step 2: Configure Address to Footprint Linkages
-----------------------------------------------


Step 3: Check Linkages using Intersects
---------------------------------------

The first of the matching stages. This step checks for and any buildings and addresses 
that directly intersect with each other.

.. code-block:: python

    def check_for_intersects(address_pt, footprint_indexes):
        '''Similar to the get nearest linkage function except this looks for intersects (uses within because its much faster) and spits out the index of any intersect'''
        footprint_geometries = tuple(map(lambda index: footprint["geometry"].loc[footprint.index == index], footprint_indexes))
        inter = tuple(map(lambda bf: address_pt.within(bf.iloc[0]), footprint_geometries))
        if True in inter:
            t_index = inter.index(True)
            return int(footprint_geometries[t_index].index[0])

    addresses['intersect_index'] = addresses[["geometry", "footprint_index"]].apply(lambda row: check_for_intersects(*row), axis=1)
    # Clean footprints remove none values and make sure that the indexes are integers
    intersections = addresses.dropna(axis=0, subset=['intersect_index'])

    addresses = addresses[addresses.intersect_index.isna()] # Keep only address points that were not intersects
    addresses.drop(columns=['intersect_index'], inplace=True) # Now drop the now useless intersects_index column

    intersect_a_points = list(set(intersections.intersect_index.tolist()))

    addresses.dropna(axis=0, subset=['footprint_index'], inplace=True)

    intersections['intersect_index'] = intersections['intersect_index'].astype(int)

    intersect_indexes = list(set(intersections.index.tolist()))

    intersections['footprint_index'] = intersections['intersect_index']
    intersections.drop(columns='intersect_index', inplace=True)
    intersections['method'] = 'intersect'


This step removes the any records that are 

Step 4: Check Linkages using Linking Data
-----------------------------------------


Step 5: Merge and Export Results
--------------------------------

The final step of the process

