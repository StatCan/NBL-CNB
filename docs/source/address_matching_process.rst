NBL-CNB: Address Matching Process
===================================

.. toctree::
   :maxdepth: 2
   
   Run Process <address_matching/run_process>
   Data Preparation <address_matching/data_prep>
   Parcel Relationship Calculation <address_matching/parcel_rel_cal>
   Matching <address_matching/matching>
   QA/QC <address_matching/qa_qc>
   Confidence Calculation <address_matching/confidence>
   Appendix <appendix/appendix_doc>

The primary goal of this section was to develop an automated process that would accurately match as many address points 
to building polygons as possible. In order to achieve this three key datasets are required:

* Address Points
* Building Footprints/Polygons 
* Parcel Fabric

Address Points and Building Footprints/Polygons are components being matched together while the Parcel Fabric acts as a
scaffolding to guide the mathcing process. Without the parcel fabric the matching process would be significantly less accurate.

The matching process is divided up into several distinct phases described in the pages below.
Also seen below is a page on how to run the matching process on your own data called 'Run Process'.
The information contained on this page gives a description on the ways to run the matching process as
well as an overview on the environments required in order to be able to run the process.

.. container:: button

    :doc:`Run Process <address_matching/run_process>` 
    :doc:`1. Data Preparation <address_matching/data_prep>`
    :doc:`2. Parcel Relationship Calculation <address_matching/parcel_rel_cal>`
    :doc:`3. Matching <address_matching/matching>`
    :doc:`4. QA/QC <address_matching/qa_qc>`
    :doc:`5. Confidence Calculation <address_matching/confidence>`
    :doc:`Appendix <appendix/appendix_doc>`

