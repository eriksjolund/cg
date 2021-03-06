"""Contains MIP DNA workflow AnalysisAPI"""
import gzip
import logging
import re
from pathlib import Path
from typing import List, Any
from ruamel.yaml import safe_load

from cg.apps import tb, hk, scoutapi, lims
from cg.apps.pipelines.fastqhandler import BaseFastqHandler
from cg.meta.deliver import DeliverAPI
from cg.store import models, Store
from cg.meta.workflow.base import get_target_bed_from_lims

COLLABORATORS = ("cust000", "cust002", "cust003", "cust004", "cust042")
MASTER_LIST = (
    "ENDO",
    "EP",
    "IEM",
    "IBMFS",
    "mtDNA",
    "MIT",
    "PEDHEP",
    "OMIM-AUTO",
    "PIDCAD",
    "PID",
    "SKD",
    "NMD",
    "CTD",
    "IF",
    "NEURODEG",
    "mcarta",
    "Cardiology",
    "BRAIN",
)
COMBOS = {
    "DSD": ("DSD", "HYP", "SEXDIF", "SEXDET"),
    "CM": ("CNM", "CM"),
    "Horsel": ("Horsel", "141217", "141201"),
}
WGS_CAPTURE_KIT = "twistexomerefseq_9.1_hg19_design.bed"


class AnalysisAPI:
    """The workflow is accessed through Trailblazer but cg provides additional conventions and
    hooks into the status database that makes managing analyses simpler"""

    def __init__(
        self,
        db: Store,
        hk_api: hk.HousekeeperAPI,
        scout_api: scoutapi.ScoutAPI,
        tb_api: tb.TrailblazerAPI,
        lims_api: lims.LimsAPI,
        deliver_api: DeliverAPI,
        yaml_loader=safe_load,
        path_api=Path,
        logger=logging.getLogger(__name__),
    ):
        self.db = db
        self.tb = tb_api
        self.hk = hk_api
        self.scout = scout_api
        self.lims = lims_api
        self.deliver = deliver_api
        self.yaml_loader = yaml_loader
        self.pather = path_api
        self.log = logger

    def check(self, family_obj: models.Family):
        """Check stuff before starting the analysis."""
        flowcells = self.db.flowcells(family=family_obj)
        statuses = []
        for flowcell_obj in flowcells:
            self.log.debug("%s: checking flowcell", flowcell_obj.name)
            statuses.append(flowcell_obj.status)
            if flowcell_obj.status == "removed":
                self.log.info("%s: requesting removed flowcell", flowcell_obj.name)
                flowcell_obj.status = "requested"
            elif flowcell_obj.status != "ondisk":
                self.log.warning("%s: {flowcell_obj.status}", flowcell_obj.name)
        return all(status == "ondisk" for status in statuses)

    def run(self, family_obj: models.Family, **kwargs):
        """Start the analysis."""
        if kwargs.get("priority") is None:
            if family_obj.priority == 0:
                kwargs["priority"] = "low"
            elif family_obj.priority > 1:
                kwargs["priority"] = "high"
            else:
                kwargs["priority"] = "normal"

        # skip MIP evaluation of QC criteria if any sample is downsampled/external
        for link_obj in family_obj.links:
            downsampled = isinstance(link_obj.sample.downsampled_to, int)
            external = link_obj.sample.application_version.application.is_external
            if downsampled or external:
                self.log.info(
                    "%s: downsampled/external - skip evaluation", link_obj.sample.internal_id
                )
                kwargs["skip_evaluation"] = True
                break

        self.tb.run(family_obj.internal_id, **kwargs)
        # mark the family as running
        family_obj.action = "running"
        self.db.commit()

    def config(self, family_obj: models.Family, pipeline: str = None) -> dict:
        """Make the MIP config. Meta data for the family is taken from the family object
        and converted to MIP format via trailblazer.

        Args:
            family_obj (models.Family):
            pipeline (str): the name of the pipeline to validate the config against

        Returns:
            dict: config_data (MIP format)
        """
        # Fetch data for creating a MIP config file
        data = self.build_config(family_obj)

        # Validate and reformat to MIP config format
        config_data = self.tb.make_config(data, pipeline)

        return config_data

    def build_config(self, family_obj: models.Family) -> dict:
        """Fetch data for creating a MIP config file."""
        data = {
            "case": family_obj.internal_id,
            "default_gene_panels": family_obj.panels,
            "samples": [],
        }
        for link in family_obj.links:
            sample_data = self._get_sample_data(link)
            if sample_data["analysis_type"] == "wgs":
                sample_data["capture_kit"] = WGS_CAPTURE_KIT
            else:
                sample_data["capture_kit"] = get_target_bed_from_lims(
                    self.lims, self.db, link.sample.internal_id
                )
            if link.mother:
                sample_data["mother"] = link.mother.internal_id
            if link.father:
                sample_data["father"] = link.father.internal_id
            data["samples"].append(sample_data)
        return data

    @staticmethod
    def _get_sample_data(link: models.FamilySample) -> dict:
        """Build sample data for MIP config file"""

        return {
            "sample_id": link.sample.internal_id,
            "sample_display_name": link.sample.name,
            "analysis_type": link.sample.application_version.application.analysis_type,
            "sex": link.sample.sex,
            "phenotype": link.status,
            "expected_coverage": link.sample.application_version.application.min_sequencing_depth,
        }

    @staticmethod
    def fastq_header(line):
        """handle illumina's two different header formats
        @see https://en.wikipedia.org/wiki/FASTQ_format

        @HWUSI-EAS100R:6:73:941:1973#0/1

            HWUSI-EAS100R   the unique instrument name
            6   flowcell lane
            73  tile number within the flowcell lane
            941     'x'-coordinate of the cluster within the tile
            1973    'y'-coordinate of the cluster within the tile
            #0  index number for a multiplexed sample (0 for no indexing)
            /1  the member of a pair, /1 or /2 (paired-end or mate-pair reads only)

        Versions of the Illumina pipeline since 1.4 appear to use #NNNNNN
        instead of #0 for the multiplex ID, where NNNNNN is the sequence of the
        multiplex tag.

        With Casava 1.8 the format of the '@' line has changed:

        @EAS139:136:FC706VJ:2:2104:15343:197393 1:Y:18:ATCACG

            EAS139  the unique instrument name
            136     the run id
            FC706VJ     the flowcell id
            2   flowcell lane
            2104    tile number within the flowcell lane
            15343   'x'-coordinate of the cluster within the tile
            197393  'y'-coordinate of the cluster within the tile
            1   the member of a pair, 1 or 2 (paired-end or mate-pair reads only)
            Y   Y if the read is filtered, N otherwise
            18  0 when none of the control bits are on, otherwise it is an even number
            ATCACG  index sequence


        TODO: add unit test
        """

        rs = {"lane": None, "flowcell": None, "readnumber": None}

        parts = line.split(":")
        if len(parts) == 5:  # @HWUSI-EAS100R:6:73:941:1973#0/1
            rs["lane"] = parts[1]
            rs["flowcell"] = "XXXXXX"
            rs["readnumber"] = parts[-1].split("/")[-1]
        if len(parts) == 10:  # @EAS139:136:FC706VJ:2:2104:15343:197393 1:Y:18:ATCACG
            rs["lane"] = parts[3]
            rs["flowcell"] = parts[2]
            rs["readnumber"] = parts[6].split(" ")[-1]
        if len(parts) == 7:  # @ST-E00201:173:HCLCGALXX:1:2106:22516:34834/1
            rs["lane"] = parts[3]
            rs["flowcell"] = parts[2]
            rs["readnumber"] = parts[-1].split("/")[-1]

        return rs

    def link_sample(self, fastq_handler: BaseFastqHandler, sample: str, case: str):
        """Link FASTQ files for a sample."""
        file_objs = self.hk.files(bundle=sample, tags=["fastq"])
        files = []

        for file_obj in file_objs:
            # figure out flowcell name from header
            with gzip.open(file_obj.full_path) as handle:
                header_line = handle.readline().decode()
                header_info = self.fastq_header(header_line)

            data = {
                "path": file_obj.full_path,
                "lane": int(header_info["lane"]),
                "flowcell": header_info["flowcell"],
                "read": int(header_info["readnumber"]),
                "undetermined": ("_Undetermined_" in file_obj.path),
            }
            # look for tile identifier (HiSeq X runs)
            matches = re.findall(r"-l[1-9]t([1-9]{2})_", file_obj.path)
            if len(matches) > 0:
                data["flowcell"] = f"{data['flowcell']}-{matches[0]}"
            files.append(data)

        fastq_handler.link(case=case, sample=sample, files=files)

    def panel(self, family_obj: models.Family) -> List[str]:
        """Create the aggregated panel file."""
        all_panels = self.convert_panels(family_obj.customer.internal_id, family_obj.panels)
        bed_lines = self.scout.export_panels(all_panels)
        return bed_lines

    @staticmethod
    def convert_panels(customer: str, default_panels: List[str]) -> List[str]:
        """Convert between default panels and all panels included in gene list."""
        if customer in COLLABORATORS:
            # check if all default panels are part of master list
            if all(panel in MASTER_LIST for panel in default_panels):
                return MASTER_LIST

        # the rest are handled the same way
        all_panels = set(default_panels)

        # fill in extra panels if selection is part of a combo
        for panel in default_panels:
            if panel in COMBOS:
                for extra_panel in COMBOS[panel]:
                    all_panels.add(extra_panel)

        # add OMIM to every panel choice
        all_panels.add("OMIM-AUTO")

        return list(all_panels)

    def _get_latest_raw_file(self, family_id: str, tag: str) -> Any:
        """Get a python object file for a tag and a family ."""

        analysis_files = self.deliver.get_post_analysis_files(
            case=family_id, version=False, tags=[tag]
        )
        if analysis_files:
            analysis_file_raw = self._open_bundle_file(analysis_files[0].path)
        else:
            raise self.log.warning(
                "No post analysis files received from DeliverAPI for '%s'", family_id
            )

        return analysis_file_raw

    def _open_bundle_file(self, relative_file_path: str) -> Any:
        """Open a bundle file and return it as an Python object."""

        full_file_path = self.pather(self.deliver.get_post_analysis_files_root_dir()).joinpath(
            relative_file_path
        )
        open_file = self.yaml_loader(self.pather(full_file_path).open())
        return open_file

    def get_latest_metadata(self, family_id: str) -> dict:
        """Get the latest trending data for a family."""

        mip_config_raw = self._get_latest_raw_file(family_id=family_id, tag="mip-config")

        qcmetrics_raw = self._get_latest_raw_file(family_id=family_id, tag="qcmetrics")

        sampleinfo_raw = self._get_latest_raw_file(family_id=family_id, tag="sampleinfo")

        trending = dict()

        if mip_config_raw and qcmetrics_raw and sampleinfo_raw:
            try:
                trending = self.tb.get_trending(
                    mip_config_raw=mip_config_raw,
                    qcmetrics_raw=qcmetrics_raw,
                    sampleinfo_raw=sampleinfo_raw,
                )
            except KeyError as error:
                self.log.warning(
                    "get_latest_metadata failed for '%s', missing key: %s", family_id, error.args[0]
                )
                trending = dict()

        return trending

    @staticmethod
    def is_dna_only_case(case):
        """returns if all samples of a case has dna application type"""

        for _link in case.links:
            if _link.sample.application_version.application.analysis_type in "wts":
                return False
        return True
