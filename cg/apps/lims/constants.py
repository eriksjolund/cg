PROP2UDF = {
    'application': 'Sequencing Analysis',
    'capture_kit': 'Capture Library version',
    'comment': 'Comment',
    'concentration': 'Concentration (nM)',
    'concentration_weight': 'Sample Conc.',
    'customer': 'customer',
    'data_analysis': 'Data Analysis',
    'elution_buffer': 'Sample Buffer',
    'extraction_method': 'Extraction method',
    'family_name': 'familyID',
    'formalin_fixation_time': 'Formalin Fixation Time',
    'index': 'Index type',
    'index_number': 'Index number',
    'organism': 'Strain',
    'organism_other': 'Other species',
    'pool': 'pool name',
    'post_formalin_fixation_time': 'Post Formalin Fixation Time',
    'priority': 'priority',
    'quantity': 'Quantity',
    'reference_genome': 'Reference Genome Microbial',
    'require_qcok': 'Process only if QC OK',
    'rml_plate_name': 'RML plate name',
    'sex': 'Gender',
    'source': 'Source',
    'tissue_block_size': 'Tissue Block Size',
    'target_reads': 'Reads missing (M)',
    'tumour': 'tumor',
    'volume': 'Volume (uL)',
    'well_position_rml': 'RML well position',
    'verified_organism': 'Verified organism',
}

MASTER_STEPS_UDFS_VOGUE = { ##!!!!!
    'received': {
        'steps' : ['CG002 - Reception Control (Dev)', 
                   'CG002 - Reception Control', 
                   'Reception Control TWIST v1',
                   'Reception Control no placement v1',
                   'Reception Control (RNA) v1'],
        'date_udf' : 'date arrived at clinical genomics'
    },
    'prepared': {
        'steps': ['CG002 - Aggregate QC (Library Validation) (Dev)',
                  'CG002 - Aggregate QC (Library Validation)',
                  'Aggregate QC (Library Validation) TWIST v1',
                  'Aggregate QC (Library Validation) (RNA) v2',
                  'Aggregate QC (Library Validation)']
    },
    'delivery': {
        'steps': ['CG002 - Delivery', 'Delivery v1'],
        'date_udf': 'Date delivered'
    },
    'sequenced': {
        'steps': ['CG002 - Illumina Sequencing (HiSeq X)',
                  'CG002 - Illumina Sequencing (Illumina SBS)',
                  'AUTOMATED - NovaSeq Run'],
        'date_udf': 'Finish Date',
        'nova_seq': ['AUTOMATED - NovaSeq Run'],
        'q30r1_udf': '% Bases >=Q30 R1',
        'q30r2_udf': '% Bases >=Q30 R2'
    },
    'concentration_and_nr_defrosts' : {
        'lot_nr_step': 'CG002 - End repair Size selection A-tailing and Adapter ligation (TruSeq PCR-free DNA)',
        'concentration_step': 'CG002 - Aggregate QC (Library Validation)',
        'lot_nr_udf': 'Lot no: TruSeq DNA PCR-Free Sample Prep Kit',
        'concentration_udf': 'Concentration (nM)',
        'apptags': ['WGSPCF', 'WGTPCF', 'WGLPCF']
    },
    'final_conc_and_amount_dna': {
        'amount_udf': 'Amount (ng)',
        'concentration_udf': 'Concentration (nM)',
        'concentration_step': 'CG002 - Aggregate QC (Library Validation)',
        'amount_step': 'CG002 - Aggregate QC (DNA)',
        'apptags': ['WGSLIF', 'WGTLIF', 'WGLLIF']
    },
    'microbial_library_concentration': {
        'concentration_step': 'CG002 - Aggregate QC (Library Validation)',
        'concentration_udf': 'Concentration (nM)',
        'apptags': 'NX'
        },
    'library_size_pre_hyb': { 
        'TWIST': {
            'size_step': ['pool samples TWIST v1'],
            'stage_udf': {'3999': 'Size (bp)', 
                          '2176': 'Average Size (bp)'}
        },
        'SureSelect' : {
            'size_step': ['CG002 - Amplify Adapter-Ligated Library (SS XT)'],
            'size_udf': 'Size (bp)',
            'apptags': ['EXO', 'EFT', 'PAN', 'PAL']}
        },
    'library_size_post_hyb': {
        'TWIST': {
            'size_step': ['CG002 - Sort HiSeq Samples'],
            'stage_udf': {'4005' : 'Size (bp)', 
                          '2182' : 'Average Size (bp)'}
        },
        'SureSelect': {
            'size_step': ['CG002 - Amplify Captured Libraries to Add Index Tags (SS XT)'],
            'size_udf': 'Size (bp)',
            'apptags': ['EXO', 'EFT', 'PAN', 'PAL']}
    },
    'reagent_labels': {
        'steps': {'bcl': ['Bcl Conversion & Demultiplexing (Nova Seq)'],
                  'define': ['Define Run Format and Calculate Volumes (Nova Seq)'],
                  'pre_bcl': ['STANDARD Prepare for Sequencing (Nova Seq)']},
        'udfs': {'reads' : '# Reads',
                  'target_reads': 'Reads to sequence (M)'},
        'exclue_tags': ['RM','EX','PA']  
        ## EX and PA should be included later. Fetching fraction from Poos Samples Twist 1
}}


MASTER_STEPS_UDFS = {
    'received_step': {
        'CG002 - Reception Control (Dev)': 'date arrived at clinical genomics',
        'CG002 - Reception Control': 'date arrived at clinical genomics',
        'Reception Control TWIST v1': 'date arrived at clinical genomics',
    },
    'prepared_step': {
        'CG002 - Aggregate QC (Library Validation) (Dev)',
        'CG002 - Aggregate QC (Library Validation)',
        'Aggregate QC (Library Validation) TWIST v1',
    },
    'delivery_step': {
        'CG002 - Delivery': 'Date delivered',
        'Delivery v1': 'Date delivered',
    },
    'sequenced_step': {
        'CG002 - Illumina Sequencing (HiSeq X)': 'Finish Date',
        'CG002 - Illumina Sequencing (Illumina SBS)': 'Finish Date',
        'AUTOMATED - NovaSeq Run': None,
    },
    'capture_kit_step': {
        'obsolete_CG002 - Hybridize Library  (SS XT)': 'SureSelect capture library/libraries used',
        'Hybridize Library TWIST v1': 'Bait Set',
    },
    'prep_method_step': {
        'CG002 - End repair Size selection A-tailing and Adapter ligation (TruSeq PCR-free DNA)':
        {
            'method_number': 'Method document',
            'method_version': 'Method document version',
        },
        'obsolete_CG002 - Hybridize Library  (SS XT)':
        {
            'method_number': 'Method document',
            'method_version': 'Method document versio',
        },
        'CG002 - Microbial Library Prep (Nextera)':
        {
            'method_number': 'Method',
            'method_version': 'Method Version',
        },
        'End-Repair and A-tailing TWIST v1':
        {
            'method_number': 'Method document',
            'method_version': 'Document version',
        },
    },
    'sequencing_method_step': {
        'CG002 - Cluster Generation (HiSeq X)':
        {
            'method_number': 'Method',
            'method_version': 'Version',
        },
        'CG002 - Cluster Generation (Illumina SBS)':
        {
            'method_number': 'Method Document 1',
            'method_version': 'Document 1 Version',
        },
    },
    'delivery_method_step': {
        'CG002 - Delivery':
        {
            'method_number': 'Method Document',
            'method_version': 'Method Version',
        },
        'Delivery v1':
        {
            'method_number': 'Method Document',
            'method_version': 'Method Version',
        },
    },
}

PROCESSES = {
    'sequenced_date': 'AUTOMATED - NovaSeq Run',
}
