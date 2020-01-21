import logging
from pathlib import Path

import ruamel.yaml

from cg.apps.mip_dna import files as mip_dna_files
from cg.apps.mip_rna import files as mip_rna_files
from cg.meta.store import mip_rna, mip_dna
from cg.exc import AnalysisNotFinishedError

LOG = logging.getLogger(__name__)


class AddHandler:

    @classmethod
    def add_analysis(cls, config_stream):
        """Gather information from MIP analysis to store."""
        config_raw = ruamel.yaml.safe_load(config_stream)
        config_data = mip_dna_files.parse_config(config_raw)
        sampleinfo_raw = ruamel.yaml.safe_load(Path(config_data['sampleinfo_path']).open())
        rna_analysis = cls._is_rna_analysis(sampleinfo_raw)
        if rna_analysis:
            sampleinfo_data = mip_rna_files.parse_sampleinfo_rna(sampleinfo_raw)
        else:
            sampleinfo_data = mip_dna_files.parse_sampleinfo(sampleinfo_raw)

        if sampleinfo_data['is_finished'] is False:
            raise AnalysisNotFinishedError('analysis not finished')

        if rna_analysis:
            new_bundle = mip_rna.build_bundle_rna(config_data, sampleinfo_data)
        else:
            new_bundle = mip_dna.build_bundle(config_data, sampleinfo_data)
        return new_bundle

    @staticmethod
    def _is_rna_analysis(sampleinfo_raw: dict) -> bool:
        """checks if all samples are RNA samples based on analysis type """
        return all([analysis == 'wts' for analysis in sampleinfo_raw['analysis_type'].values()])
