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

The parcel fabric is used as a guide and cut any buildings that cross the boundary using the following steps.

1. Convert parcel fabric from polygons to lines.
2. If a polygon intersects one or more of these lines then split the polygon along those lines.
3. Analyze the results and determine if the split results in two or more valid buildings. Remove any slivers.

Method
------

Step 1: Cut Geometry Data Preperation
_____________________________________

The first step is to convert the parcel fabric from polygons to lines. This is done using the following methodology:

1. Geometry is validated using the below function to repair any invalid geometries.
   
   .. code-block:: python

      def ValidateGeometry(input_geometry) -> gpd.GeoSeries:
         '''Checks if input geometry is valid and if invalid attempts to make it valid accepts Geodataframes and Geoseries'''
         if type(input_geometry) == gpd.GeoSeries:
               input_geometry = input_geometry.apply(lambda geom: make_valid(geom))
         if type(input_geometry) == gpd.GeoDataFrame:
               input_geometry = input_geometry['geometry'].apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
         return input_geometry

2. To maintain efficiency all non essential geometry is dropped from the cut_geom at this stage. This is done using two filters the first of which 
   filters out all cut geometry that does not intersect any of the building polygons.

   .. code-block:: python 
      
      # Drop Non-Essential Cut Geometry
        cut_joined = gpd.sjoin(cut_geom, self.bp[['bp_index', 'geometry']])
        cut_joined = list(set(cut_joined[~cut_joined['bp_index'].isna()]['cut_index'].tolist()))
        cut_geom = cut_geom[cut_geom['cut_index'].isin(cut_joined)]
   
   The second filter is only run if the optional point_data input is used and removes all cut geometry that does not intersect a point.
   
   .. code-block:: python
      
      if type(point_data) != None:

            point_data.to_crs(crs=crs, inplace=True)
            point_data['ap_index'] = range(1, len(point_data.index) + 1)
            cut_joined_ap = gpd.sjoin(cut_geom, point_data[['ap_index', 'geometry']])
            cut_joined_ap = list(set(cut_joined_ap[~cut_joined_ap['ap_index'].isna()]['cut_index'].tolist()))
            cut_geom = cut_geom[cut_geom['cut_index'].isin(cut_joined_ap)]


3. The geometry is then checked for type and converted into lines if necessary using the following process:

   1. If the input geometry is not a LineString or MultiLineString and is a Polygon or Multipolygon then convert it to lines using .boundary.
   2. .boundary return the boundary as a single line. Break this up so that each side is a single record per side.
   3. The above steps create significant number of duplicated lines filter the duplicated geometries to prevent duplication
    
   .. code-block:: python
      
      def ToSingleLines(geom: shapely.geometry) -> MultiLineString:
            '''Converts polygons into single lines'''
                
            def MultiLineDevolver(m_line_string: MultiLineString) -> list:
                '''Converts a multilinestring into a list of its component lines'''
                m_line_string = [l for l in m_line_string.geoms]
                m_line_string = [list(map(LineString, zip(l.coords[:-1], l.coords[1:]))) for l in m_line_string]
                m_line_string = [ls for l in m_line_string for ls in l]
                return m_line_string

            # temp measure to remove GeometryCollections and None cases
            if geom.geom_type not in ['MultiPolygon', 'Polygon', 'LineString', 'MultiLineString', 'Point', 'MultiPoint']:
                # Temp block in place until a solution is found for GeometryCollections
                print(geom)
                sys.exit()
                return None

      def check_geom(input_gdf: gpd.GeoDataFrame, geometry_column= 'geometry') -> gpd.GeoDataFrame:
            '''Checks to see if the input  geometry is a line. If polygon converts to lines. If points or other returns a geometry error'''                         

            #input_gdf.reset_index(inplace=True)
            if input_gdf.geometry[0].geom_type in ['LineString', 'MultiLineString']:
                # If the geometry is already in line type
                return input_gdf
            
            # If inputs are polygons then convert them to lines
            if input_gdf.geometry[0].geom_type in ['Polygon', 'MultiPolygon']:
                
                # explode to remove multipolygons
                input_gdf = input_gdf.explode(index_parts=False)
                # convert linestrings into single linestrings 
                input_gdf['single_lines'] = input_gdf['geometry'].swifter.apply(lambda p: ToSingleLines(p))
                # explode list output of prior function
                output_gdf = input_gdf.explode('single_lines')
                # switch geometry to the new geom and drop old geom
                output_gdf = SwapGeometry(output_gdf, 'geometry', 'single_lines')

                return output_gdf

            # If the geometry is a point or mutipoint raise an error
            if input_gdf.geometry[0].geom_type in ['Point', 'MultiPoint']:
                raise IOError('Shape is not a Polygon or Line')

3.
   
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

2. Polygons that intersect a line are then split along the lines that they intersect and a new MultiPolygon object is returned.
   
   .. code-block:: python

       def CutPolygon(intersect_indexes: tuple, in_geom: Polygon, line_geom:gpd.GeoDataFrame, cut_field:str) -> MultiPolygon:
            '''Cuts the input polygon by the lines linked to it during the FindIntersects Step Run the FindIntersects step before calling this function'''
           
            # Select only key vars and set the cut indexes
            line_geom = line_geom[[cut_field, 'geometry']]
            cut_indexes = intersect_indexes

            # Polygons with no intersects don't need to be split
            if len(cut_indexes) == 0:
                return in_geom
            
            # Polygons with intersects need to be split
            if len(cut_indexes) >= 1:
                # retrieve the records related to the cut indexes
                cutters = line_geom[line_geom[cut_field].isin(cut_indexes)]
                
                # convert to a single LineString or MultiLineString
                cut_single = [shapely.ops.linemerge(cutters.geometry.values.tolist())]
                
                # Convert the polygon into its boundary and append it to the cut lines list
                cut_single.append(in_geom.boundary)
                # Create a union between all the lines
                cut_single = shapely.ops.unary_union(cut_single)
                # merge all the lines into a single LineString or MultiLineString
                cut_single = shapely.ops.linemerge(cut_single)
                # Convert the linemerge result back into a polygon
                polygons = shapely.ops.polygonize(cut_single)
                # Ensure result is a MultiPolygon and return it
                return MultiPolygon(polygons)


       bp[cut_geom] = bp[['geometry', 'line_ints']].apply(lambda x: CutPolygon(x, self.line_geom[['cut_index', 'geometry']]), axis=1)

3. The returned geometry is then exploded to create a record for each polygon within the multipoloygon.
   
   .. code-block:: python
      
      bp = bp.explode(index_parts=True)

All valid input polygons have now been split by any lines in the cut geometry that they intersected. The outputs can now be cleaned.      

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

1. The area of each split is calculated and any polygons under 50m2 are removed
   
   .. code-block:: python
      
      bp['split_area'] = bp.area

2. A spatial join is then created between the polygons and the parcels and any polygons that do not intersect a parcel are removed.
   This removes polygons that overhang into roadways, easements, etc.
   
   .. code-block:: python

      bp = bp.sjoin

3. 
