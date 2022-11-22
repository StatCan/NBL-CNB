Step 1: Data Preparation
===================================

.. contents:: Contents:
   :depth: 4

Overview
========
There are three key layers that must be injested, cleaned, and prepped before matching can begin.
The composition of these input files varies widely by jurisdiction so to a certain degree this process
will vary slightly from region to region in order to compensate for these differences. These three layers
are:

* Building Footprints
* Address Points
* Parcel Fabric

All three of these layers must be available in order to to create address to building matches under the
current process.

Parcel Fabric Cleaning
----------------------

The following  cleaning/preparation processes are applied to the raw parcel data in order to 
prepare for matching:

* Micro Parcel detection/removal
* Linkage field selection / calculation

Micro Parcel Detection / Removal

Micro parcels are small parcels with an area smaller than 100m2. These parcels are most often located in 
trailer parks and condo developments. These only conplicate the matching process when included and are
therefore removed during the cleaning phase.

Address Points Cleaning
-----------------------

The following  cleaning/preparation processes are applied to the raw address point data in order to 
prepare for matching:

Building Footprint Cleaning
---------------------------

The following  cleaning/preparation processes are applied to the raw building footprint data in order to 
prepare for matching:

* Parcel Linkage
* Non-Addressable Outbuilding Detection

Parcel Linkages are made similar to the way they are made for address points with minor changes in workfolow.

* Building polygons are converted to representative points to allow for the creation of the spatial jurisdiction
* If a building intersects more than one polygon then the smallest acceptable polygon is taken as the linkage.

**Representative Point** A representative point is an arbitrary points within a polygon. The key feature of this point is 
that it will always be contained within the bounds of a polygon regardless of complexity. This is different from a centroid
which is always located at the centre of the polygon regardless of if it actually sits within the bounds of that polygon or not.

Non-Addressable outbuilding detection:

A building is considered to be a non Non-Addressable outbuilding when one or more of the following criteria are met:

* The footprint has an area of less than 50m2 and there is at least one other building greater than 50m2 in the same parcel,
* The area of the building is between 50m2 and 100m2 and the number of buildings is greater than the number of address points in the parcel
* The building is determined exceed the acceptable threshold of roundness. The roundness of the building is determined using the following formula:
   
   .. math::
      
      (4*pi*building_area)/(building_perimiter*building_perimiter)

   Should a building have a roundness of >= 0.98 then it is considered to be Non-Addressable Outbuilding.


..  code-block:: python

