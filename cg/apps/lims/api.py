# -*- coding: utf-8 -*-
import datetime as dt
import logging

from genologics.entities import Sample, Process, Project, Artifact
from genologics.lims import Lims
from dateutil.parser import parse as parse_date
import operator


from cg.exc import LimsDataError
from .constants import PROP2UDF, MASTER_STEPS_UDFS, PROCESSES
from .order import OrderHandler

# fixes https://github.com/Clinical-Genomics/servers/issues/30
import requests_cache

requests_cache.install_cache(backend="memory")

SEX_MAP = {"F": "female", "M": "male", "Unknown": "unknown", "unknown": "unknown"}
REV_SEX_MAP = {value: key for key, value in SEX_MAP.items()}
AM_METHODS = {
    "1464": "Automated TruSeq DNA PCR-free library preparation method",
    "1317": "HiSeq X Sequencing method at Clinical Genomics",
    "1383": "MIP analysis for Whole genome and Exome",
    "1717": "NxSeq® AmpFREE Low DNA Library Kit (Lucigen)",
    "1060": "Raw data delivery",
    "1036": "HiSeq 2500 Rapid Run sequencing",
    "1314": "Automated SureSelect XT Target Enrichment for Illumina sequencing",
    "1518": "200 ng input Manual SureSelect XT Target Enrichment",
    "1079": "Manuel SureSelect XT Target Enrichment for Illumina sequencing",
    "1879": "Method - Manual Twist Target Enrichment",
    "1830": "NovaSeq 6000 Sequencing method",
}
METHOD_INDEX, METHOD_NUMBER_INDEX, METHOD_VERSION_INDEX = 0, 1, 2

LOG = logging.getLogger(__name__)


class LimsAPI(Lims, OrderHandler):
    def __init__(self, config):
        lconf = config["lims"]
        super(LimsAPI, self).__init__(
            lconf["host"], lconf["username"], lconf["password"]
        )

    def sample(self, lims_id: str):
        """Fetch a sample from the LIMS database."""
        lims_sample = Sample(self, id=lims_id)
        data = self._export_sample(lims_sample)
        return data

    def lims_sample(self, lims_id: str):
        """Fetch a sample from the LIMS database."""
        return Sample(self, id=lims_id)

    def samples_in_pools(self, pool_name, projectname):
        return self.get_samples(
            udf={"pool name": str(pool_name)}, projectname=projectname
        )

    def _export_project(self, lims_project):
        return {
            "id": lims_project.id,
            "name": lims_project.name,
            "date": parse_date(lims_project.open_date)
            if lims_project.open_date
            else None,
        }

    def _export_sample(self, lims_sample):
        """Get data from a LIMS sample."""
        udfs = lims_sample.udf
        data = {
            "id": lims_sample.id,
            "name": lims_sample.name,
            "project": self._export_project(lims_sample.project),
            "family": udfs.get("familyID"),
            "customer": udfs.get("customer"),
            "sex": SEX_MAP.get(udfs.get("Gender"), None),
            "father": udfs.get("fatherID"),
            "mother": udfs.get("motherID"),
            "source": udfs.get("Source"),
            "status": udfs.get("Status"),
            "panels": udfs.get("Gene List").split(";")
            if udfs.get("Gene List")
            else None,
            "priority": udfs.get("priority"),
            "received": self.get_received_date_obs(lims_sample.id),
            "application": udfs.get("Sequencing Analysis"),
            "application_version": (
                int(udfs["Application Tag Version"])
                if udfs.get("Application Tag Version")
                else None
            ),
            "comment": udfs.get("comment"),
        }
        return data

    def _export_artifact(self, lims_artifact):
        """Get data from a LIMS artifact."""
        return {"id": lims_artifact.id, "name": lims_artifact.name}

    def get_received_date_obs(self, lims_id: str) -> str:
        """Get the date when a sample was received."""

        step_names_udfs = MASTER_STEPS_UDFS["received_step"]

        received_dates = self._get_all_step_dates(step_names_udfs, lims_id)
        received_date = self._most_recent_date(received_dates)

        return received_date

    def get_prepared_date_obs(self, lims_id: str) -> dt.datetime:
        """Get the date when a sample was prepared in the lab."""

        step_names_udfs = MASTER_STEPS_UDFS["prepared_step"]
        prepared_dates = []

        for process_type in step_names_udfs:
            artifacts = self.get_artifacts(
                process_type=process_type, samplelimsid=lims_id
            )

            for artifact in artifacts:
                prepared_dates.append(parse_date(artifact.parent_process.date_run))

        if prepared_dates:
            sorted_dates = sorted(prepared_dates, reverse=True)
            prepared_date = sorted_dates[0]

        return prepared_date if prepared_dates else None

    def get_delivery_date_obs(self, lims_id: str) -> dt.date:
        """Get delivery date for a sample."""

        step_names_udfs = MASTER_STEPS_UDFS["delivery_step"]

        delivered_dates = self._get_all_step_dates(
            step_names_udfs, lims_id, artifact_type="Analyte"
        )

        if len(delivered_dates) > 1:
            LOG.warning("multiple delivery artifacts found for: %s", lims_id)

        delivered_date = self._most_recent_date(delivered_dates)

        return delivered_date

    def get_sequenced_date_obs(self, lims_id: str) -> dt.date:
        """Get the date when a sample was sequenced."""
        novaseq_process = PROCESSES["sequenced_date"]

        step_names_udfs = MASTER_STEPS_UDFS["sequenced_step"]

        sequenced_dates = self._get_all_step_dates(step_names_udfs, lims_id)

        novaseq_artifacts = self.get_artifacts(
            process_type=novaseq_process, samplelimsid=lims_id
        )

        if novaseq_artifacts and novaseq_artifacts[0].parent_process.date_run:
            sequenced_dates.append(
                (
                    novaseq_artifacts[0].parent_process.date_run,
                    parse_date(novaseq_artifacts[0].parent_process.date_run),
                )
            )

        if len(sequenced_dates) > 1:
            LOG.warning("multiple sequence artifacts found for: %s", lims_id)

        sequenced_date = self._most_recent_date(sequenced_dates)

        return sequenced_date

    def capture_kit(self, lims_id: str) -> str:
        """Get capture kit for a LIMS sample."""

        step_names_udfs = MASTER_STEPS_UDFS["capture_kit_step"]
        capture_kits = set()

        lims_sample = Sample(self, id=lims_id)
        capture_kit = lims_sample.udf.get("Capture Library version")
        if capture_kit and capture_kit != "NA":
            return capture_kit
        else:
            for process_type in step_names_udfs:
                artifacts = self.get_artifacts(
                    samplelimsid=lims_id, process_type=process_type, type="Analyte"
                )
                udf_key = step_names_udfs[process_type]
                capture_kits = capture_kits.union(
                    self._find_capture_kits(artifacts, udf_key)
                    or self._find_twist_capture_kits(artifacts, udf_key)
                )

        if len(capture_kits) > 1:
            message = f"Capture kit error: {lims_sample.id} | {capture_kits}"
            raise LimsDataError(message)

        if len(capture_kits) == 1:
            return capture_kits.pop()

        return None

    def get_samples(self, *args, map_ids=False, **kwargs):
        """Bypass to original method."""
        lims_samples = super(LimsAPI, self).get_samples(*args, **kwargs)
        if map_ids:
            lims_map = {
                lims_sample.name: lims_sample.id for lims_sample in lims_samples
            }
            return lims_map
        else:
            return lims_samples

    def family(self, customer: str, family: str):
        """Fetch information about a family of samples."""
        filters = {"customer": customer, "familyID": family}
        lims_samples = self.get_samples(udf=filters)
        samples_data = [
            self._export_sample(lims_sample) for lims_sample in lims_samples
        ]
        # get family level data
        family_data = {"family": family, "customer": customer, "samples": []}
        priorities = set()
        panels = set()

        for sample_data in samples_data:
            priorities.add(sample_data["priority"])
            if sample_data["panels"]:
                panels.update(sample_data["panels"])
            family_data["samples"].append(sample_data)

        if len(priorities) == 1:
            family_data["priority"] = priorities.pop()
        elif "express" in priorities:
            family_data["priority"] = "express"
        elif "priority" in priorities:
            family_data["priority"] = "priority"
        elif "standard" in priorities:
            family_data["priority"] = "standard"
        else:
            raise LimsDataError(f"unable to determine family priority: {priorities}")

        family_data["panels"] = list(panels)
        return family_data

    def process(self, process_id: str) -> Process:
        """Get LIMS process."""
        return Process(self, id=process_id)

    def process_samples(self, lims_process: Process):
        """Retrieve LIMS input samples from a process."""
        for lims_artifact in lims_process.all_inputs():
            for lims_sample in lims_artifact.samples:
                yield lims_sample.id

    def update_sample(
        self,
        lims_id: str,
        sex=None,
        application: str = None,
        target_reads: int = None,
        priority=None,
        data_analysis=None,
        name: str = None,
    ):
        """Update information about a sample."""
        lims_sample = Sample(self, id=lims_id)
        if sex:
            lims_gender = REV_SEX_MAP.get(sex)
            if lims_gender:
                lims_sample.udf[PROP2UDF["sex"]] = lims_gender
        if application:
            lims_sample.udf[PROP2UDF["application"]] = application
        if isinstance(target_reads, int):
            lims_sample.udf[PROP2UDF["target_reads"]] = target_reads
        if priority:
            lims_sample.udf[PROP2UDF["priority"]] = priority
        if data_analysis:
            lims_sample.udf[PROP2UDF["data_analysis"]] = data_analysis
        if name:
            lims_sample.name = name

        lims_sample.put()

    def update_project(self, lims_id: str, name=None):
        """Update information about a project."""
        lims_project = Project(self, id=lims_id)
        if name:
            lims_project.name = name
            lims_project.put()

    def get_prep_method(self, lims_id: str) -> str:
        """Get the library preparation method."""

        step_names_udfs = MASTER_STEPS_UDFS["prep_method_step"]

        return self._get_methods(step_names_udfs, lims_id)

    def get_sequencing_method(self, lims_id: str) -> str:
        """Get the sequencing method."""

        step_names_udfs = MASTER_STEPS_UDFS["sequencing_method_step"]

        return self._get_methods(step_names_udfs, lims_id)

    def get_delivery_method(self, lims_id: str) -> str:
        """Get the delivery method."""

        step_names_udfs = MASTER_STEPS_UDFS["delivery_method_step"]

        return self._get_methods(step_names_udfs, lims_id)

    def get_processing_time(self, lims_id):
        received_at = self.get_received_date(lims_id)
        delivery_date = self.get_delivery_date(lims_id)
        if received_at and delivery_date:
            return delivery_date - received_at

    @staticmethod
    def _sort_by_date_run(sort_list: list):
        """
        Sort list of tuples by parent process attribute date_run in descending order.

        Parameters:
            sort_list (list): a list of tuples in the format (date_run, elem1, elem2, ...)

        Returns:
            sorted list of tuples
        """
        return sorted(sort_list, key=lambda sort_tuple: sort_tuple[0], reverse=True)

    def _most_recent_date(self, dates: list):
        """
        Gets the most recent date from a list of dates sorted by date_run

        Parameters:
            dates (list): a list of tuples in the format (date_run, date), sorted by date_run
            descending

        Returns:
            The date in the first tuple in dates
        """
        sorted_dates = self._sort_by_date_run(dates)
        date_run_index = 0
        date_index = 1

        return sorted_dates[date_run_index][date_index] if dates else None

    def _get_methods(self, step_names_udfs, lims_id):
        """
        Gets the method, method number and method version for a given list of stop names
        """
        methods = []

        for process_name in step_names_udfs:
            artifacts = self.get_artifacts(
                process_type=process_name, samplelimsid=lims_id
            )
            if artifacts:
                udf_key_number = step_names_udfs[process_name]["method_number"]
                udf_key_version = step_names_udfs[process_name]["method_version"]
                methods.append(
                    (
                        artifacts[0].parent_process.date_run,
                        self.get_method_number(artifacts[0], udf_key_number),
                        self.get_method_version(artifacts[0], udf_key_version),
                    )
                )

        sorted_methods = self._sort_by_date_run(methods)

        if sorted_methods:
            method = sorted_methods[METHOD_INDEX]

            if method[METHOD_NUMBER_INDEX] is not None:
                method_name = AM_METHODS.get(method[METHOD_NUMBER_INDEX])
                return (
                    f"{method[METHOD_NUMBER_INDEX]}:{method[METHOD_VERSION_INDEX]} - "
                    f"{method_name}"
                )

        return None

    def _get_all_step_dates(self, step_names_udfs, lims_id, artifact_type=None):
        """
        Gets all the dates from artifact bases on process type and associated udfs, sample lims id
        and optionally the type
        """
        dates = []

        for process_type in step_names_udfs:
            artifacts = self.get_artifacts(
                process_type=process_type, samplelimsid=lims_id, type=artifact_type
            )

            for artifact in artifacts:
                udf_key = step_names_udfs[process_type]
                if artifact.parent_process and artifact.parent_process.udf.get(udf_key):
                    dates.append(
                        (
                            artifact.parent_process.date_run,
                            artifact.parent_process.udf.get(udf_key),
                        )
                    )

        return dates

    def _str_to_datetime(self, date: str)-> dt:
        if date is None:
            return None
        return dt.datetime.strptime(date, '%Y-%m-%d')


    def get_sequenced_date(self, sample: Sample)-> dt:
        """Get the date when a sample passed sequencing.
        
        This will return the last time that the sample passed sequencing.
        """

        process_types = MASTER_STEPS_UDFS['sequenced_step']

        sample_udfs = sample.udf.get( 'Passed Sequencing QC')
        if not sample_udfs:
            return None
        final_date = None

        artifact = self._get_output_artifact(process_types=process_types.keys(), 
                                             lims_id=sample.id, last=True)
        if artifact:
            parent_process = artifact.parent_process
            print(process_types[parent_process.type.name])
            final_date = parent_process.udf.get(process_types[parent_process.type.name]['date_udf'])
            if final_date:
                final_date = dt.datetime.combine(final_date, dt.time.min)
            else:
                final_date = self._str_to_datetime(artifact.parent_process.date_run)
            

        return final_date
        

    def get_received_date(self, sample: Sample)-> dt:
        """Get the date when a sample was received.
        """

        process_types = MASTER_STEPS_UDFS['received_step']
        processes = self.get_processes(type=process_types.keys(), inputartifactlimsid=sample.artifact.id)
        if not processes:
            return None
        first_process = processes[0]
        for process in processes:
            if process.date_run < first_process.date_run:
                first_process=processes
        date_udf = process_types[first_process.type.name]['date_udf']
        date_arrived = first_process.udf.get(date_udf)
        if date_arrived:
            # We need to convert datetime.date to datetime.datetime
            datetime_arrived = self._str_to_datetime(date_arrived.isoformat())
        else:
            date_arrived = first_process.date_run
            datetime_arrived = self._str_to_datetime(date_arrived)

        return datetime_arrived 

    def get_prepared_date(self, sample: Sample)-> dt:
        """Get the first date when a sample was prepared in the lab.
        """
        process_types = MASTER_STEPS_UDFS['prepared_step']

        artifact = self._get_output_artifact(process_types=process_types, lims_id=sample.id, last=False)

        prepared_date = None
        if artifact:
            prepared_date = self._str_to_datetime(artifact.parent_process.date_run)

        return prepared_date

    def get_delivery_date(self, sample: Sample)-> dt:
        """Get delivery date for a sample.
        
        This will return the first time a sample was delivered
        """

        process_types = MASTER_STEPS_UDFS['delivery_step']
        
        artifact = self._get_output_artifact(process_types=process_types.keys(), lims_id=sample.id, last=False)
        delivery_date = None
        
        art_date = None
        if artifact:
            parent_process = artifact.parent_process
            art_date = parent_process.udf.get(process_types[parent_process.type.name]['date_udf'])
        
        if art_date:
            # We need to convert datetime.date to datetime.datetime
            delivery_date = self._str_to_datetime(art_date.isoformat())

        return delivery_date


    def get_number_of_days(self, first_date: dt, second_date : dt) -> int:
        """Get number of days between different time stamps."""

        days = None
        if first_date and second_date:
            time_span = second_date - first_date
            days = time_span.days

        return days

    def _get_output_artifact(self, process_types: list, lims_id: str, last: bool = True) -> Artifact:
        """Returns the output artifact related to lims_id and the step that was first/latest run.
        
        If last = False return the first artifact
        """
        artifacts = self.get_artifacts(samplelimsid = lims_id, process_type = process_types)
        
        artifact = None
        date = None
        for art in artifacts:
            # Get the date of the artifact
            new_date = self._str_to_datetime(art.parent_process.date_run)
            if not new_date:
                continue
            # If this is the first artifact we initialise the variables
            if not date:
                date = new_date
            if not artifact:
                artifact = art
                continue
            # If we want the latest artifact check if new date is newer than existing
            if last:
                if new_date > date:
                    artifact = art
                    date = new_date
            # If we want the first artifact check if new date is older than existing
            else:
                if new_date < date:
                    artifact = art
                    date = new_date

        return artifact


    def _get_latest_input_artifact(self, process_type: str, lims_id: str) -> Artifact:
        """Returns the input artifact related to lims_id and the step that was latest run."""

        latest_input_artifact = None
        artifacts = self.get_artifacts(samplelimsid = lims_id, process_type = process_type) 
        # Make a list of tuples (<date the artifact was generated>, <artifact>): 
        date_art_list = list(set([(a.parent_process.date_run, a) for a in artifacts]))
        if date_art_list:
            #Sort on date:
            date_art_list.sort(key = operator.itemgetter(0))
            #Get latest:
            dummy, latest_outart = date_art_list[-1] #get latest
            #Get the input artifact related to our sample
            for inart in latest_outart.input_artifact_list():
                if lims_id in [sample.id for sample in inart.samples]:
                    latest_input_artifact = inart 
                    break        

        return latest_input_artifact


    def get_concentration_and_nr_defrosts(self, application_tag: str, lims_id: str) -> dict:
        """Get concentration and nr of defrosts for wgs illumina PCR-free samples.
        Find the latest artifact that passed through a concentration_step and get its 
        concentration_udf. --> concentration
        Go back in history to the latest lot_nr_step and get the lot_nr_udf from that step. --> lotnr
        Find all steps where the lot_nr was used. --> all_defrosts
        Pick out those steps that were performed before our lot_nr_step --> defrosts_before_this_process
        Count defrosts_before_this_process. --> nr_defrosts"""

        if not application_tag:
            return {}

        if not application_tag[0:6] in MASTER_STEPS_UDFS['concentration_and_nr_defrosts']['apptags']:
            return {}

        lot_nr_step = MASTER_STEPS_UDFS['concentration_and_nr_defrosts']['lot_nr_step']
        concentration_step = MASTER_STEPS_UDFS['concentration_and_nr_defrosts']['concentration_step']
        lot_nr_udf = MASTER_STEPS_UDFS['concentration_and_nr_defrosts']['lot_nr_udf']
        concentration_udf = MASTER_STEPS_UDFS['concentration_and_nr_defrosts']['concentration_udf']

        return_dict = {}
        concentration_art = self._get_latest_input_artifact(concentration_step, lims_id)
        if concentration_art:
            concentration = concentration_art.udf.get(concentration_udf)
            lotnr = concentration_art.parent_process.udf.get(lot_nr_udf)
            this_date = self._str_to_datetime(concentration_art.parent_process.date_run)

            # Ignore if multiple lot numbers:
            if lotnr and len(lotnr.split(',')) == 1 and len(lotnr.split(' ')) == 1:
                all_defrosts = self.get_processes(type = lot_nr_step, udf = {lot_nr_udf : lotnr})
                defrosts_before_this_process = []

                # Find the dates for all processes where the lotnr was used (all_defrosts),
                # and pick the once before or equal to this_date
                for defrost in all_defrosts:
                    if defrost.date_run and self._str_to_datetime(defrost.date_run) <= this_date:
                        defrosts_before_this_process.append(defrost)

                nr_defrosts = len(defrosts_before_this_process)

                return_dict = {'nr_defrosts' : nr_defrosts, 'concentration' : concentration, 
                                'lotnr' : lotnr, 'concentration_date' : this_date}

        return return_dict


    def get_final_conc_and_amount_dna(self, application_tag: str, lims_id: str) -> dict:
        """Find the latest artifact that passed through a concentration_step and get its 
        concentration. Then go back in history to the latest amount_step and get the amount."""

        if not application_tag:
            return {}

        if not application_tag[0:6] in MASTER_STEPS_UDFS['final_conc_and_amount_dna']['apptags']:
            return {}

        return_dict = {}
        amount_udf = MASTER_STEPS_UDFS['final_conc_and_amount_dna']['amount_udf']
        concentration_udf = MASTER_STEPS_UDFS['final_conc_and_amount_dna']['concentration_udf']
        concentration_step = MASTER_STEPS_UDFS['final_conc_and_amount_dna']['concentration_step']
        amount_step = MASTER_STEPS_UDFS['final_conc_and_amount_dna']['amount_step']

        concentration_art = self._get_latest_input_artifact(concentration_step, lims_id)
        if concentration_art:
            amount_art = None
            step = concentration_art.parent_process
            # Go back in history untill we get to an output artifact from the amount_step
            while step and not amount_art:
                art = self._get_latest_input_artifact(step.type.name, lims_id)
                if amount_step in [p.type.name for p in self.get_processes(inputartifactlimsid=art.id)]:
                    amount_art = art
                step = art.parent_process
            
            amount = amount_art.udf.get(amount_udf) if amount_art else None
            concentration = concentration_art.udf.get(concentration_udf)
            return_dict = {'amount' : amount, 'concentration':concentration}

        return return_dict


    def get_microbial_library_concentration(self, application_tag: str, lims_id: str) -> float:
        """Check only samples with mictobial application tag.
        Get concentration_udf from concentration_step."""

        if not application_tag:
            return {}

        if not application_tag[3:5] == MASTER_STEPS_UDFS['microbial_library_concentration']['apptags']:
            return None

        concentration_step = MASTER_STEPS_UDFS['microbial_library_concentration']['concentration_step']
        concentration_udf = MASTER_STEPS_UDFS['microbial_library_concentration']['concentration_udf']

        concentration_art = self._get_latest_input_artifact(concentration_step, lims_id)

        if concentration_art:
            return concentration_art.udf.get(concentration_udf)
        else:
            return None



    def get_library_size(self, app_tag: str, lims_id: str, workflow: str, hyb_type: str) -> int:
        """Getting the udf Size (bp) that in fact is set on the aggregate qc librar validation step.
        But since the same qc protocol is used both for pre-hyb and post-hyb, there is no way to 
        distiguish from within the aggregation step, wether it is pre-hyb or post-hyb qc. 
        Because of that, we instead search for
            TWIST: the input artifact of the output artifacts of the steps that are AFTER the 
            aggregations step:
                For pre hyb: MASTER_STEPS_UDFS['pre_hyb']['TWIST'].get('size_step')
                For post hyb: MASTER_STEPS_UDFS['post_hyb']['TWIST'].get('size_step')
            SureSelect: the output artifacts of the steps that are BEFORE the aggregations step:
                For pre hyb: MASTER_STEPS_UDFS['pre_hyb']['SureSelect'].get('size_step')
                For post hyb: MASTER_STEPS_UDFS['post_hyb']['SureSelect'].get('size_step')"""
    
        size_steps = MASTER_STEPS_UDFS[hyb_type][workflow].get('size_step')

        if workflow == 'TWIST':
            stage_udfs = MASTER_STEPS_UDFS[hyb_type][workflow].get('stage_udf')
            out_art=self._get_output_artifact(size_steps, lims_id, last=True)
            if out_art:
                sample = Sample(self, id=lims_id)
                for inart in out_art.parent_process.all_inputs():
                    stage = inart.workflow_stages[0].id
                    if sample in inart.samples and stage in stage_udfs:
                        size_udf = stage_udfs[stage]
                        return inart.udf.get(size_udf)
        elif workflow == 'SureSelect':
            if not app_tag or app_tag[0:3] not in MASTER_STEPS_UDFS[hyb_type][workflow]['apptags']:
                return None
            size_art = self._get_output_artifact(size_steps, lims_id, last=True)
            if size_art:
                size_udf = MASTER_STEPS_UDFS[hyb_type][workflow].get('size_udf')
                return size_art.udf.get(size_udf)
        
        return None

    @staticmethod
    def get_method_number(artifact, udf_key_number):
        """
        get method number for artifact
        """
        return artifact.parent_process.udf.get(udf_key_number)

    @staticmethod
    def get_method_version(artifact, udf_key_version):
        """
        get method version for artifact
        """
        return artifact.parent_process.udf.get(udf_key_version)

    @staticmethod
    def _find_capture_kits(artifacts, udf_key):
        """
        get capture kit from parent process for non-TWIST samples
        """
        capture_kits = set(
            artifact.parent_process.udf.get(udf_key)
            for artifact in artifacts
            if artifact.parent_process.udf.get(udf_key) is not None
        )
        return capture_kits

    @staticmethod
    def _find_twist_capture_kits(artifacts, udf_key):
        """
        get capture kit from parent process for TWIST samples
        """
        capture_kits = set(
            artifact.udf.get(udf_key)
            for artifact in artifacts
            if artifact.udf.get(udf_key) is not None
        )
        return capture_kits
