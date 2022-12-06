Polygon Splitting
=================

.. toctree::
   :maxdepth: 2
   :hidden:

As sources of building data were compiled for the NBL a problem was noted. Buildings that were close together in 
some sources were clumped together into a single polygon. This had significant implications for the accuracy of
matching process. As seen in the first image below out area of interest has a row of single family detached homes
which while relatively close together should be individual polygons in a building layer.

.. image:: img/clumped_sat_img.png
   :width: 400
   :alt: Sat image of clumped area

However that is not what we see in the data. As seen in the image below this area is clumped into long single polygons
that are not representative of what exists on the ground. 

.. image:: img/clumped_polys.png
   :width: 400
   :alt: Sat image of clumped polygons

As things stand performing the matching process on this area would produce highly inaccurate results. In order to improve
the results of the matching process the method described below was developed.

Method Overview
---------------

As we can see below there is a ready made method available for dealing with the clumped buildings. As seen in the image
below the parcels when overlaid over the building data cuts the buildings at approximately the correct location.

.. image:: img/clumped_w_parcels.png
   :width: 400
   :alt: Sat image of clumped polygons

We will use the parcel fabric as a guide and cut any buildings that cross the boundary using the following steps.

1. Convert parcel fabric from polygons to lines.
2. If a polygon intersects one or more of these lines then split the polygon along those lines.
3. Analyze the results and determine if the split results in two or more valid buildings. Remove any slivers.

Method
------
Step 1: Convert Parcels to lines
__________________________________

The first step is to convert the parcel fabric from polygons to lines. To do this the following method is followed.

1. 

Step 2: Polygon Splitting
_________________________


Step 3: Clean-up and Analysis
_____________________________

Now that the polygons are split clean-up on the output is done in order to ensure data quality. The following things are 
checked for during this step:

1. If any slivers* have been created
2. If the created splits should be considered valid splits or not
3. 


**Sliver**: Any polygon that is the result of a split with an area of less an 50m2.