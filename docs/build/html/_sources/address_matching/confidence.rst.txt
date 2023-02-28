Step 5: Match Confidence Calculation
====================================

.. toctree::
    :maxdepth: 2
    :hidden:

For reference, the descriptions on this page cover the code in **match_confidence_calc.py**

The final step of the matching process is the confidence calculation. Confidence is a numeric score
calculated based on the characteristics of the match. Additionally, secondary sources such as the
National Address Register (NAR) are brought in to add to the calculation wherever possible. It is 
important to note that the confidence score is an arbitrary number and should not be considered a 
percentage.

As the number of available sources can vary widely depending on the region of work the below score each
breakdown should be considered an example and the number of sources included in the initial score. The 
final score will vary from region to region. 

Base Scores
-----------

The base score is the initial value assigned to a match based on the relationship
between the number of address points and the number of building polygons in the 
linked parcel (if available). This score is based on the complexity of the relationship
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

Link distance is a key indicator for the accuracy of a match. The shorter the distance
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

Final Classification
--------------------

Once all available confidence modifiers are added to the score the value is classified into confidence types.
These classifications and the scores required to attain them can be seen below:

.. csv-table::
    :file: csv/confidence_types.csv
    :header-rows: 1

Method
------

The information described above is put into use in the following way:

1. Where possible the address data is checked against available secondary sources (NAR, municipal-level civic address sources, etc). A boolean flag system is used to
   indicate whether or not the address appears in a given secondary source. Then during the main confidence calculation, the 
   score is changed based on whether the value returned was True or False.
2. In cases where we are classifying a value into a category (link distance, etc) the value in question is compared against the table and the
   appropriate value is added or subtracted from the score as needed.
3. The total score is then classified into a confidence type LOW, MEDIUM, or HIGH based on the result of the score calculation.
4. The results are then added to the line link values from the qa/qc step for easier visualisation.
5. All results are exported to the project geopackage.

The code for the above process can be seen below:

.. code-block:: python
    
    def civics_flag_builder(civic_num, str_nme, str_type, mun_civics, civics_number_field='civic_num', civics_sname_field='st_nme', civics_stype_field='st_type'):
        '''Creates the confidence flags for a match and returns the following output:
        
        1: Address value matches a civic address that fall in same parcel
        0: Address value does not match civic that fall in same parcel
        -1: No civic value in parcel or no underlying parcel to compare
        
        Inputs should be prefiltered to only the records associated with the adp and parcel in question
        str_type is currently unused but can be added in in the future
        '''
        # if no municipal civics are present return -1
        if len(mun_civics) == 0:
            return -1

        check_address = mun_civics.loc[(mun_civics[civics_number_field].map(int) == int(civic_num)) & (mun_civics[civics_sname_field] == str_nme)]
        if len(check_address) == 0:
            # as there was no match on street name return 0
            return 0
        
        if len(check_address) >= 1:
            return 1

        print(civic_num, str_nme)
        print(check_address)
        sys.exit()


    def parcel_location_flag_builder(address_row, parcel_row):
        '''
        Compares the address data for address points against linked parcels (if available). A full, partial, or false match is determined and a flag of the correct type is
        placed on the record. 

        outputs the following flags:

        0 - Address point and parcel address match do not match
        1 - Address point and parcel address match
        -1 - Underlying parcel issue (either no underlying parcel or no valid underlying address)

        '''
        
        # For cases where there are no underlying parcel but should be filtered out before being put through this function
        if len(parcel_row) == 0:
            return -1
        
        a_list = address_row.tolist()
        p_list = parcel_row.iloc[0].tolist()

        # if cadastral data has no civic number then we return cad_ncn as no accuracy comparison can ba made
        if not isinstance(p_list[1], str):
            return -1 # cadastral data no civic number

        # parcel (cadastral) and address point address part values in simple vars
        adp_civic = int(a_list[1])
        cad_min = int(p_list[1])
        cad_max = int(p_list[2])
        adp_sname = a_list[2] 
        cad_sname = p_list[3]
        # adp_stype = a_list[-1]
        # cad_stype = p_list[-1]

        # Setup flag vars as false
        flag_count = 0

        if (adp_civic >= cad_min) and (adp_civic <= cad_max):
            flag_count += 1
        if adp_sname == cad_sname:
            flag_count += 1

        if flag_count > 0:
            return 1
        if flag_count == 0:
            return 0

        print(parcel_row)
        print(address_row)
        sys.exit()


    def confidence_score_calculator(parcel_rel, mun_civ_flag, parcel_loc_flag, link_len, method, nar_link, sbgr_link):
        '''Returns a match confidence score based on key fields calculated during the matching process. Use only as part of an apply function on a single record'''
        parcel_rel_scores = {'one_to_one' : 60,
                            'one_to_many' : 55, 
                            'many_to_one' : 50, 
                            'many_to_many' : 40, 
                            'unlinked' : 30, 
                            'manual' : 100,
                            'other' : 0}
        
        method_scores = {
            'intersect' : 7,
            'data_linking' : 3,
            '20m_buffer' : 0,
            '20m_buffer_bp' : 0
        }

        confidence = 0

        # initial calculation based on the parcel relationship
        if parcel_rel in parcel_rel_scores:
            confidence += parcel_rel_scores[parcel_rel]
        else:
            confidence += parcel_rel_scores['other']
        
        # MODIFIER #1: Secondary Address Sources (municipal civic, NAR, parcel location)
        if mun_civ_flag == 1:
            confidence += 5
        # Commented out until new solution is found
        # if parcel_loc_flag == 1:
        #     confidence += 5

        # MODIFIER #2 Link Distance 
        if link_len <= 5:
            confidence += 10
        if (link_len > 5) and (link_len <= 20):
            confidence += 5
        if (link_len > 20) and (link_len <= 50):
            confidence += 1
        if (link_len > 50) and (link_len <= 200): # Here just to visualize the category. Doesn't change score
            confidence += 0
        if (link_len > 200) and (link_len <= 400): # Score reduction starts here
            confidence -= 10
        
        # MODIFIER #3: NAR and SBgR Linkages
        if nar_link == 1:
            confidence += 10
        if sbgr_link == 1:
            confidence += 5

        # MODIFIER #4: Link Method
        if method in method_scores:
            confidence += method_scores[method]
        else:
            confidence += 0

        return confidence


    def valid_confidence_input_counter(mun_civ_flag, parcel_loc_flag, link_len, method, nar_link, sbgr_link):
        '''Returns the number of valid modifiers on the parcel relationship score that were used to help calculate the confidence value. 
        Parcel relationship is not included in this calculation.'''

        v_score = 0 
        # For preflagged modifiers check for the match flag
        for mod in [mun_civ_flag, nar_link, sbgr_link]: #parcel_loc_flag]:
            if mod == 1:
                v_score += 1
        
        # Specific checks for other flags
        
        # For link len check that the link len is within the lowest positive scoring distance (<50)
        if link_len < 50:
            v_score +=1
        
        # For method add only methods that contribute to a positive score
        if method in ['intersect', 'data_linking']:
            v_score +=1
        # Add other specific modifiers here if they become available
        
        return v_score


    def total_confidence_input_counter(mun_civ_flag, parcel_loc_flag, link_len, method, nar_link, sbgr_link):
        '''Returns the total number of confidence modifiers that had a valid input (
            modifiers with an invalid input -1 or NULL are excluded from this calculation)'''
        
        i_score = 0 
        
        # For preflagged modifiers check if the record doesn't equal the invalid flag
        for mod in [mun_civ_flag, nar_link, sbgr_link]:# parcel_loc_flag]:
            if mod != -1:
                i_score += 1
        # If score is between 0 and 50 take as a positive indicator (50 being the lowest positive category)
        if (link_len >= 0.0) and (link_len <= 50.0):
            i_score +=1
        
        if type(method) == str:
            i_score += 1
        
        return i_score


    def determine_confidence_type(con_score):
        '''Returns a string denoting the level of confidence in the match based on the integer value of a given input field (usually 'confidence')'''

        if con_score >= 70:
            return 'HIGH'
        if (con_score >= 60) and (con_score < 70):
            return 'MEDIUM'
        else:
            return 'LOW'

        addresses = gpd.read_file(qa_qc_gpkg, layer=addresses_lyr_nme, crs=proj_crs)

        parcels = gpd.read_file(project_gpkg, layer=parcel_lyr_nme, crs=proj_crs)

        # Create flags for secondary address sources

        if mun_civic_lyr_nme not in fiona.listlayers(mun_civic_gpkg):
            print('No municipal civics data available')
            addresses['mun_civic_flag'] = np.NaN
        else:
            mun_civics = gpd.read_file(mun_civic_gpkg, layer=mun_civic_lyr_nme, crs=proj_crs, driver='GPKG')
            print('Prepping municipal civic fields')
            mun_civics['st_nme'] = mun_civics['st_nme'].str.upper().str.replace(' ', '')
            print('Creating municipal civics flag')
            addresses['mun_civic_flag'] = addresses[['link_field', 'number', 'street', 'stype_en']].apply(lambda row: civics_flag_builder(row[1],row[2],row[3],mun_civics[mun_civics['link_field'] == row[0]]), axis=1) 

        addresses['parcel_loc_flag'] = np.NaN

        if 'nar_addr_guid' in addresses.columns.tolist():
            addresses['nar_link_flag'] = addresses['nar_addr_guid'].apply(lambda x: 1 if type(x) == str else 0)

        else:
            addresses['nar_link_flag'] = np.NaN

        if 'sbgr_bg_sn' in addresses.columns.tolist():
            addresses['sbgr_link_flag'] = addresses['sbgr_bg_sn'].apply(lambda x: 1 if type(x) == str else 0)

        else:
            addresses['sbgr_link_flag'] = np.NaN

    # Calculate confidence score and associated fields
    confidence_vars = ['parcel_rel', 'mun_civic_flag', 'parcel_loc_flag', 'link_length', 'method', 'nar_link_flag', 'sbgr_link_flag']

    addresses['confidence'] = addresses[confidence_vars].apply(lambda row: confidence_score_calculator(*row), axis=1)

    addresses['con_valid_inputs'] = addresses[confidence_vars[1:]].apply(lambda row: valid_confidence_input_counter(*row), axis=1)
    addresses['con_total_inputs'] = addresses[confidence_vars[1:]].apply(lambda row: total_confidence_input_counter(*row), axis=1)

    addresses['confidence_type'] = addresses['confidence'].apply(lambda c: determine_confidence_type(c))

    # Add confidence to line links
    lines_gdf = gpd.read_file(qa_qc_gpkg, layer=line_link_lyr_nme)
    lines_gdf = lines_gdf.merge(addresses[['link_id', 'confidence', 'confidence_type']], on='link_id')
