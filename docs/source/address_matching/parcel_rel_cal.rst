Step 2: Parcel Relationship Calculation
=======================================

.. toctree::
   :maxdepth: 2
   :hidden:

Once cleaned the data's relationship to the parcel data must be calculated. This relationship
is based on the count of address points and building footprints contained in a given parcel.

Relationship Types
==================
One to One
----------
The most basic relationship type where in a given single parcel there is only one address point 
and one building footprint.

One to Many
-----------
In this relationship type there is one address point but many building footprints contained in a
single parcel.

Many to One
-----------
In this relationship there are many address points and a single building footprint contained in a
single parcel

Many to Many
------------
This is the most complicated relationship type where more than one address point and more than one
building footprint are contained in a single parcel.

Code
----
.. code-block:: python

