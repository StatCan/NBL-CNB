Step 5: Match Confidence Calculation
====================================

.. toctree::
    :maxdepth: 2
    :hidden:

Step 5 Overview
===============

For reference the descriptions on this page cover the code in **match_confidence_calc.py**

The final step of the matching process is the confidence calculation. Confidence is a numeric score
calculated based off the characteristics of the match. Additionally, secondary sources such as the
National Address Register (NAR) are brought in to add to the calculation wherever possible. It is 
important to note that the confidence score is an arbitrary number and should not be considered an
indicator percent confidence.

As the number of available sources can vary wildly depending on the region of work the below score
breakdown should be considered an example and the number of sources included in the initial score 
caculation will vary from region to region. 

Base Scores
-----------

The base score is the initial value assigned to a match based on the relationship
between the number of address points and the number of building polygons in the 
linked parcel (if available). This score is based off the complexity of the relationship,
or lack of relationship in cases where there is no linked parcel.

.. csv-table:: 
    :file: csv/base.csv
    :header-rows: 1

Match Method
------------

The method used to make the match is also taken into account as seen in the table 
below.

.. csv-table:: 
    :file: csv/match_method.csv
    :header-rows: 1

**20m_bp** only applies to linkages that fall within the big parcel matching method. 

Link Distance
-------------

Link distance is a key indicator on the accuracy of a match. The shorter the distance
between the address point and the building footprint 

.. csv-table:: 
    :file: csv/link_distance.csv
    :header-rows: 1

Other Secondary Sources
-----------------------

Secondary sources from both internal and external data providers are also incorporated
into the confidence score.

Internal data sources such as the National Address Register (NAR) and the Statistical Building Register (SBgR)
are utilized.

.. csv-table:: 
    :file: csv/internal_link.csv
    :header-rows: 1

Wherever possible authoritative external sources are used to validate the match. Some examples
of a secondary source include: a civic address point layer from a city within the AOI, or an address
field in the parcel data used to make the matches.

.. csv-table:: 
    :file: csv/secondary_sources.csv
    :header-rows: 1


