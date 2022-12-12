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

All code samples in this section are pulled from the scripts/polygon_cutter.py script found in the github repo.

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

The first step is to convert the parcel fabric from polygons to lines. To do this the following method is used.

1. Geometry is validated using the below function to repair any invalid geometries.
   
   .. code-block:: python

      def ValidateGeometry(input_geometry) -> gpd.GeoSeries:
         '''Checks if input geometry is valid and if invalid attempts to make it valid accepts Geodataframes and Geoseries'''
         if type(input_geometry) == gpd.GeoSeries:
               input_geometry = input_geometry.apply(lambda geom: make_valid(geom))
         if type(input_geometry) == gpd.GeoDataFrame:
               input_geometry = input_geometry['geometry'].apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
         return input_geometry

2. The geometry is then checked for type and converted into lines if necessary using the below function:
   
   .. code-block:: python
      
      def check_geom(input_gdf: gpd.GeoDataFrame, geometry_column= 'geometry') -> gpd.GeoDataFrame:
         '''Checks to see if the input  geometry is a line. If polygon converts to lines. If points or other returns a geometry error'''
         input_gdf.reset_index(inplace=True)
         if input_gdf.geometry[0].geom_type in ['LineString', 'MultiLineString']:
               # If the geometry is already in line type then just strip attributes 
               return input_gdf
         
         # If inputs are polygons then convert them to lines and strip attributes
         if input_gdf.geometry[0].geom_type in ['Polygon', 'MultiPolygon']:
               
               input_gdf['geometry'] = input_gdf['geometry'].apply(lambda p: p.boundary)
               return input_gdf.explode(index_parts=True)
   
Step 2: Polygon Splitting
_________________________

To split the polygons the following process is followed:

1. A linkage is created between every line and building polygon where they intersect using a spatial join.
   
   .. code-block:: python

      def FindIntersects(input_geom: gpd.GeoDataFrame, search_geometry: gpd.GeoDataFrame, input_link_field: str, search_link_field: str) -> gpd.GeoDataFrame:
         '''finds all intersections between the input geometry and the search geometry'''

         joined_geom = gpd.sjoin(input_geom, search_geometry[[search_link_field, 'geometry']], op='intersects')
         input_geom['line_ints'] = input_geom[input_link_field].apply(lambda x: tuple(joined_geom[joined_geom[input_link_field] == x][search_link_field].tolist()))
         return input_geom 

2. Polygons that intersect a line are then split 


Step 3: Clean-up and Analysis
_____________________________

Now that the polygons are split clean-up on the output is done in order to ensure data quality. The following things are 
checked for during this step:

1. If any slivers* have been created.
2. If the created splits should be considered valid. 
3. Ensure that the output splits are linkable back to the original polygon for future QA/QC

**Sliver**: Any polygon that is the result of a split with an area of less an 50m2.

This step is essential as not every split should be considered valid. for example, in the image below the building crosses
two parcel boundaries and will therefore be cut twice.

.. image:: img/complex_ex.png
   :width: 400
   :alt: Example with valid and invalid splits

There are two cuts that will occur when this building is split. One around the mid-point of the structure and one in the bottom
corner of the polygon. Looking at the underlying imagery (see below) we can see the the split at the mid-point is most likely a
valid split. The second smaller split is most likely a sliver based off its size and the imagery. It can safely be removed from 
the dataset and isolated.

.. image:: img/complex_img.png
   :width: 400
   :alt: Example with valid and invalid splits with imagery

The cleaning process looks as follows: