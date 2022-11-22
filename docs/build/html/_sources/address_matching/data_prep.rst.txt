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

Parcel data is the most variable dataset in terms of what the geometry looks like and what fields are 
available in open data portals. Cleaning this data is the most variable of the three datasets

Address Points Cleaning
-----------------------

Address Points are cleaned using the following method

Building Footprint Cleaning
---------------------------

The following  cleaning/preparation processes are applied to the raw building footprint data in order to 
prepare for matching:

* Non-Addressable Outbuilding Detection
* Parcel Linkage


Non-Addressable outbuilding detection:

A non Non-Addressable outbuilding is defined as a 

..  code-block:: python

