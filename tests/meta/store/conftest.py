""" fixtures for storing RNA analysis unit tests  """
import datetime
from pathlib import Path
import ruamel

import pytest


@pytest.fixture(scope="function")
def config_stream(files):
    """ config stream fixture """
    return {
        "rna_config_store": Path(files["rna_config_store"]).open(),
    }


@pytest.fixture(scope="function")
def config_raw(files_raw):
    """ config stream fixture """
    return files_raw["rna_config_store"]


@pytest.fixture(scope="function")
def config_data():
    """ config data fixture """
    return {
        "email": None,
        "case": "case_id",
        "samples": [{"id": "sample_id", "type": "wts"}],
        "is_dryrun": False,
        "out_dir": "tests/fixtures/apps/mip/rna/store",
        "priority": "low",
        "sampleinfo_path": "tests/fixtures/apps/mip/rna/store/case_qc_sample_info.yaml",
    }


@pytest.fixture(scope="function")
def sampleinfo_data():
    """ sampleinfo data fixture """
    return {
        "date": datetime.datetime(2020, 3, 1),
        "is_finished": True,
        "case": "case_id",
        "version": "v8.2.2",
    }


@pytest.fixture(scope="function")
def deliverables_raw(config_data):
    """ raw_deliverables fixture """
    return ruamel.yaml.safe_load(Path(config_data["out_dir"], "case_id_deliverables.yaml").open())


@pytest.fixture(scope="function")
def bundle_data():
    """ bundle data fixture """
    return ruamel.yaml.safe_load(open("tests/fixtures/apps/mip/rna/store/bundle_data.yaml"))
