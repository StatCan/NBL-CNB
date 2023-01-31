NBL-CNB: Address Matching Process
===================================

.. toctree::
   :maxdepth: 1
   
   Run Process <address_matching/run_process>
   Data Preparation <address_matching/data_prep>
   Parcel Relationship Calculation <address_matching/parcel_rel_cal>
   Matching <address_matching/matching>
   QA/QC <address_matching/qa_qc>
   Confidence Calculation <address_matching/confidence>
   

The primary goal of this section was to develop an automated process that would accurately match as many address points 
to building polygons as possible. In order to achieve this three key datasets were required:

* Address Points
* Building Footprints/Polygons 
* Parcel Fabric

The Parcel Fabric acts as a scaffolding to guide the matching process. Without the parcel fabric the matching process would be 
significantly less accurate.

The matching process is divided up into several distinct phases as seen below. Also contained below is a page on how to run the matching 
process on your own data called 'Run Process'. The information contained on this page gives a description on the ways to run the 
matching process as well as an overview on the environments required in order to be able to run the process.

.. container:: button

    :doc:`Run Process <address_matching/run_process>` 
    :doc:`1. Data Preparation <address_matching/data_prep>`
    :doc:`2. Parcel Relationship Calculation <address_matching/parcel_rel_cal>`
    :doc:`3. Matching <address_matching/matching>`
    :doc:`4. QA/QC <address_matching/qa_qc>`
    :doc:`5. Confidence Calculation <address_matching/confidence>`
    

