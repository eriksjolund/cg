"""Fixtures for cli balsamic tests"""
from datetime import datetime
import pytest

from cg.apps.hk import HousekeeperAPI
from cg.store import Store, models
from cg.apps.tb import TrailblazerAPI

from tests.store_helpers import ensure_customer, add_family, add_sample


@pytest.fixture
def balsamic_store_context(balsamic_store, balsamic_case) -> dict:
    """context to use in cli"""
    return {
        "hk_api": MockHouseKeeper(balsamic_case.internal_id),
        "db": balsamic_store,
        "tb_api": MockTB(),
        "balsamic": {"root": "root", "conda_env": "conda_env"},
    }


class MockTB(TrailblazerAPI):
    """Mock of trailblazer """

    def __init__(self):
        """Override TrailblazerAPI __init__ to avoid default behaviour"""

    def analyses(
        self,
        *,
        family: str = None,
        query: str = None,
        status: str = None,
        deleted: bool = None,
        temp: bool = False,
        before: datetime = None,
        is_visible: bool = None,
        workflow=None
    ):
        """Override TrailblazerAPI analyses method to avoid default behaviour"""
        return []


class MockHouseKeeper(HousekeeperAPI):
    """Mock HousekeeperAPI"""

    def __init__(self, bundle_name):
        """Override HousekeeperAPI method to avoid default behaviour"""
        self._store = MockHousekeeperStore()
        self.bundle_name = bundle_name
        self.bundle_data = None
        self.root_dir = "root_dir"

    def get_files(self, bundle: str, tags: list, version: int = None):
        """return a list of mocked files"""
        del tags, bundle, version
        return [MockFile()]

    def add_bundle(self, data: dict):
        """fake adding a bundle in housekeeper"""

        if not self.bundle_data or self.bundle_data["name"] != data["name"]:
            self.bundle_data = data
            return MockBundle(data=data, name=self.bundle_name), MockVersion()

        return None


class MockHousekeeperStore:
    """Mock Store of Housekeeper"""

    def __init__(self):
        """Override __init__ to avoid default behaviour"""
        self.root_dir = ""

    def add_commit(self, *pargs, **kwargs):
        """Implements add_commit to allow it to be used in HousekeeperAPI"""


class MockBundle:
    """Mock Bundle"""

    def __init__(self, data, name):
        """Implement minimal set of properties to allow it to be used in test"""
        self.name = name
        self._data = data


class MockVersion:
    """Mock Version"""

    def __init__(self):
        """Implement minimal set of properties to allow it to be used in test"""
        self.created_at = datetime.now()
        self.included_at = None
        self.relative_root_dir = ""
        self.files = []


class MockFile:
    """Mock File"""

    def __init__(self, path=""):
        """Implement minimal set of properties to allow it to be used in test"""
        self.path = path
        self.full_path = path


@pytest.fixture(scope="function")
def balsamic_store(base_store: Store) -> Store:
    """real store to be used in tests"""
    _store = base_store

    case = add_family(_store, "balsamic_case")
    tumour_sample = add_sample(_store, "tumour_sample", is_tumour=True)
    normal_sample = add_sample(_store, "normal_sample", is_tumour=False)
    _store.relate_sample(case, tumour_sample, status="unknown")
    _store.relate_sample(case, normal_sample, status="unknown")

    case = add_family(_store, "mip_case")
    normal_sample = add_sample(_store, "normal_sample", is_tumour=False, data_analysis="mip")
    _store.relate_sample(case, normal_sample, status="unknown")

    _store.commit()

    return _store


@pytest.fixture(scope="function")
def config_file():
    """Get the path to a balsamic case config file"""
    return "tests/fixtures/apps/balsamic/case/config.json"


@pytest.fixture(scope="function")
def deliverables_file():
    """Return a balsamic deliverables file"""
    return "tests/fixtures/apps/balsamic/case/metadata.yml"


@pytest.fixture(scope="function")
def deliverables_file_directory():
    """Return a balsamic deliverables file containing a directory"""
    return "tests/fixtures/apps/balsamic/case/metadata_directory.yml"


@pytest.fixture(scope="function")
def deliverables_file_tags():
    """Return a balsamic deliverables file containing one file with two tags"""
    return "tests/fixtures/apps/balsamic/case/metadata_file_tags.yml"


@pytest.fixture(scope="function")
def balsamic_case(analysis_store) -> models.Family:
    """case with balsamic data_type"""
    return analysis_store.find_family(ensure_customer(analysis_store), "balsamic_case")


@pytest.fixture(scope="function")
def mip_case(analysis_store) -> models.Family:
    """case with balsamic data_type"""
    return analysis_store.find_family(ensure_customer(analysis_store), "mip_case")