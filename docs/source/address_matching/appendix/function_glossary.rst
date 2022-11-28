Function Glossary
=================

.. toctree::
   :maxdepth: 2
   :hidden:

This section contains documentation for the functions that appear in the process and basic information about each.


Matching matching_master
------------------------

.. py:function:: groupby_to_list(df, group_field, list_field)

   Helper function: faster alternative to pandas groupby.apply/agg(list).
   Groups records by one or more fields and compiles an output field into a list for each group.
    
   :param df: dataframe to group
   :type df: DataFrame
   :param group_field: the field to group on
   :type group_field: str or list
   :param list_field: field to list by
   :type list_field: str
   :return: A pandas series with the list
   :rtype: pd.Series

.. py:function:: get_unlinked_geometry(address_gdf, footprint_gdf, buffer_distance)
   Returns indexes for the building polygon based on the increasing buffer size'

   :param address_gdf: geodataframe of addresses to check
   :type df: GeoDataFrame
   :param footprint_gdf: geodataframe of buildings to check
   :type group_field: GeoDataFrame
   :param buffer_distance: the maximum size of the buffer in metres
   :type list_field: int

   