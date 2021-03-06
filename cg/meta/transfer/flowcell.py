"""API for transfer a flowcell"""

import logging
from typing import List

from cg.apps.hk import HousekeeperAPI
from cg.apps.stats import StatsAPI
from cg.store import Store, models

LOG = logging.getLogger(__name__)


class TransferFlowcell:
    """Transfer flowcell API"""

    def __init__(self, db: Store, stats_api: StatsAPI, hk_api: HousekeeperAPI = None):
        self.db = db
        self.stats = stats_api
        self.hk = hk_api

    def transfer(self, flowcell_name: str, store: bool = True) -> models.Flowcell:
        """Populate the database with the information."""
        if store and self.hk.tag("fastq") is None:
            self.hk.add_commit(self.hk.new_tag("fastq"))
        if store and self.hk.tag(flowcell_name) is None:
            self.hk.add_commit(self.hk.new_tag(flowcell_name))
        stats_data = self.stats.flowcell(flowcell_name)
        flowcell_obj = self.db.flowcell(flowcell_name)
        if flowcell_obj is None:
            flowcell_obj = self.db.add_flowcell(
                name=flowcell_name,
                sequencer=stats_data["sequencer"],
                sequencer_type=stats_data["sequencer_type"],
                date=stats_data["date"],
            )
        flowcell_obj.status = "ondisk"
        for sample_data in stats_data["samples"]:
            LOG.debug(f"adding reads/fastqs to sample: {sample_data['name']}")
            sample_obj = self.db.sample(sample_data["name"]) or self.db.microbial_sample(
                sample_data["name"]
            )
            if sample_obj is None:
                LOG.warning(f"unable to find sample: {sample_data['name']}")
                continue

            if store:
                self.store_fastqs(
                    sample=sample_obj.internal_id,
                    flowcell=flowcell_name,
                    fastq_files=sample_data["fastqs"],
                )

            sample_obj.reads = sample_data["reads"]
            enough_reads = (
                sample_obj.reads > sample_obj.application_version.application.expected_reads
            )
            newest_date = (sample_obj.sequenced_at is None) or (
                flowcell_obj.sequenced_at > sample_obj.sequenced_at
            )
            if enough_reads and newest_date:
                sample_obj.sequenced_at = flowcell_obj.sequenced_at

            if isinstance(sample_obj, models.Sample):
                flowcell_obj.samples.append(sample_obj)
            if isinstance(sample_obj, models.MicrobialSample):
                flowcell_obj.microbial_samples.append(sample_obj)

            LOG.info(
                f"added reads to sample: {sample_data['name']} - {sample_data['reads']} "
                f"[{'DONE' if enough_reads else 'NOT DONE'}]"
            )

        return flowcell_obj

    def store_fastqs(self, sample: str, flowcell: str, fastq_files: List[str]):
        """Store FASTQ files for a sample in housekeeper."""
        hk_bundle = self.hk.bundle(sample)
        if hk_bundle is None:
            hk_bundle = self.hk.new_bundle(sample)
            self.hk.add_commit(hk_bundle)
            new_version = self.hk.new_version(created_at=hk_bundle.created_at)
            hk_bundle.versions.append(new_version)
            self.hk.commit()
            LOG.info(f"added new Housekeeper bundle: {hk_bundle.name}")

        with self.hk.session_no_autoflush():
            hk_version = hk_bundle.versions[0]
            for fastq_file in fastq_files:
                if self.hk.files(path=fastq_file).first() is None:
                    LOG.info(f"found FASTQ file: {fastq_file}")
                    tags = [self.hk.tag("fastq"), self.hk.tag(flowcell)]
                    new_file = self.hk.new_file(path=fastq_file, tags=tags)
                    hk_version.files.append(new_file)
            self.hk.commit()
