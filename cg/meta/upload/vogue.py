"""API to run Vogue"""
# -*- coding: utf-8 -*-
import json

from cg.apps.gt import GenotypeAPI
from cg.apps.vogue import VogueAPI
from cg.apps.lims import LimsAPI
from cg.apps.lims.constants import PROP2UDF, TEST_SAMPLES
from cg.store import Store
from datetime import date, timedelta

import logging
import datetime as dt


LOG = logging.getLogger(__name__)


class UploadVogueAPI:
    """API to load data into Vogue"""

    def __init__(
        self, genotype_api: GenotypeAPI, vogue_api: VogueAPI, store: Store, lims_api: LimsAPI
    ):
        self.genotype_api = genotype_api
        self.vogue_api = vogue_api
        self.store = store
        self.lims_api = lims_api

    def load_genotype(self, days):
        """Loading genotype data from the genotype database into the trending database"""
        samples = self.genotype_api.export_sample(days=days)
        samples = json.loads(samples)
        for sample_id, sample_dict in samples.items():
            sample_dict["_id"] = sample_id
            self.vogue_api.load_genotype_data(sample_dict)

        samples_analysis = self.genotype_api.export_sample_analysis(days=days)
        samples_analysis = json.loads(samples_analysis)
        for sample_id, sample_dict in samples_analysis.items():
            sample_dict["_id"] = sample_id
            self.vogue_api.load_genotype_data(sample_dict)

    def load_apptags(self):
        """Loading application tags from statusdb into the trending database"""
        apptags = self.store.applications()
        apptags_for_vogue = []
        for tag in apptags.all():
            apptags_for_vogue.append(
                {"tag": tag.tag, "prep_category": tag.prep_category}
            )

        self.vogue_api.load_apptags(apptags_for_vogue)

    def load_flowcells(self, days):
        """Loading flowcells from lims into the trending database"""

        self.vogue_api.load_flowcells(days=days)


    def load_sample(self, lims_sample=None, lims_sample_id=None):
        """Function to load one lims sample into the database"""

        if not lims_sample:
            lims_sample = self.lims_api.lims_sample(lims_sample_id)

        if lims_sample.id in TEST_SAMPLES:
            return

        sample_for_vogue = self.build_sample(sample=lims_sample)
        print(sample_for_vogue)
        #self.vogue_api.load_samples(samples_for_vogue)


    def load_samples(self, days):
        """Function to load all lims samples into the database"""
        some_days_ago = date.today() - timedelta(days=days) 
        the_date = some_days_ago.strftime("%Y-%m-%dT00:00:00Z")
        latest_processes = self.lims_api.get_processes(last_modified = the_date)
        samples = []
        LOG.info('Found %s processes modified since %s.', len(latest_processes), the_date)
        LOG.info('Fetching recently updated samples...')
        for process in latest_processes:
            for analyte in process.all_inputs():
                samples += analyte.samples
        unique_samples = set(samples)
        nr_unique_samples = len(unique_samples)
        LOG.info('%s samples will be added or updated.', nr_unique_samples)
        for nr, sample in enumerate(unique_samples):
            LOG.info('%s/%s %s' % (nr, nr_unique_samples, sample.id))
            self.load_sample(lims_sample=sample)  


    def build_sample(self, sample)-> dict:
        """Parse lims sample"""

        application_tag = sample.udf.get(PROP2UDF['application'])
        #category = adapter.get_category(application_tag) 
        
        mongo_sample = {'_id' : sample.id}
        mongo_sample['family'] = sample.udf.get(PROP2UDF['family_name'])
        mongo_sample['strain'] = sample.udf.get(PROP2UDF['organism'])
        mongo_sample['source'] = sample.udf.get(PROP2UDF['source'])
        mongo_sample['customer'] = sample.udf.get(PROP2UDF['customer'])
        mongo_sample['priority'] = sample.udf.get(PROP2UDF['priority'])
        mongo_sample['initial_qc'] = sample.udf.get(PROP2UDF['passed_initial_qc'])
        mongo_sample['library_qc'] = sample.udf.get(PROP2UDF['passed_library_qc'])
        mongo_sample['sequencing_qc'] = sample.udf.get(PROP2UDF['passed_sequencing_qc'])
        mongo_sample['application_tag'] = application_tag
        #mongo_sample['category'] = category

        conc_and_amount = self.lims_api.get_final_conc_and_amount_dna(application_tag, sample.id)
        mongo_sample['amount'] = conc_and_amount.get('amount')
        mongo_sample['amount-concentration'] = conc_and_amount.get('concentration')

        concentration_and_nr_defrosts = self.lims_api.get_concentration_and_nr_defrosts(application_tag, sample.id)
        mongo_sample['nr_defrosts'] = concentration_and_nr_defrosts.get('nr_defrosts')
        mongo_sample['nr_defrosts-concentration'] = concentration_and_nr_defrosts.get('concentration')
        mongo_sample['lotnr'] = concentration_and_nr_defrosts.get('lotnr')

        sequenced_at = self.lims_api.get_sequenced_date(sample)
        received_at = self.lims_api.get_received_date(sample)
        prepared_at = self.lims_api.get_prepared_date(sample)
        delivered_at = self.lims_api.get_delivery_date(sample)

        mongo_sample['sequenced_date'] = sequenced_at
        mongo_sample['received_date'] = received_at
        mongo_sample['prepared_date'] = prepared_at
        mongo_sample['delivery_date'] = delivered_at
        mongo_sample['sequenced_to_delivered'] = self.lims_api.get_number_of_days(sequenced_at, delivered_at)
        mongo_sample['prepped_to_sequenced'] = self.lims_api.get_number_of_days(prepared_at, sequenced_at)
        mongo_sample['received_to_prepped'] = self.lims_api.get_number_of_days(received_at, prepared_at)
        mongo_sample['received_to_delivered'] = self.lims_api.get_number_of_days(received_at, delivered_at)

        mongo_sample['microbial_library_concentration'] = self.lims_api.get_microbial_library_concentration(application_tag, sample.id)
        
        mongo_sample['library_size_pre_hyb'] = self.lims_api.get_library_size(application_tag, sample.id, 
                                                                'TWIST', 'library_size_pre_hyb')
        mongo_sample['library_size_post_hyb'] = self.lims_api.get_library_size(application_tag, sample.id, 
                                                                'TWIST', 'library_size_post_hyb')
        if not mongo_sample['library_size_post_hyb']:
            if not received_at or received_at < dt.datetime(2019, 1, 1):
                mongo_sample['library_size_pre_hyb'] = self.lims_api.get_library_size(application_tag, sample.id, 
                                                                    'SureSelect', 'library_size_pre_hyb')
                mongo_sample['library_size_post_hyb'] = self.lims_api.get_library_size(application_tag, sample.id, 
                                                                    'SureSelect', 'library_size_post_hyb')

        for key in list(mongo_sample.keys()):
            if mongo_sample[key] is None:
                mongo_sample.pop(key)

        return mongo_sample