"""Fixtures for store tests"""
import datetime as dt

import pytest

# Files fixtures


@pytest.fixture
def application_versions_file(fixtures_dir):
    """"application version import file"""
    _file = fixtures_dir / "store/api/application_versions.xlsx"
    return str(_file)


@pytest.fixture
def applications_file(fixtures_dir):
    """"application import file"""
    _file = fixtures_dir / "store/api/applications.xlsx"
    return str(_file)


@pytest.fixture(name="microbial_submitted_order")
def fixture_microbial_submitted_order():
    """Build an example order as it looks after submission to ."""

    def _get_item(name: str, internal_id: str, well_position: str, organism: str) -> dict:
        """Return a item"""
        ref_genomes = {
            "C. Jejuni": "NC_111",
            "M. upium": "NC_222",
            "C. difficile": "NC_333",
        }
        item = dict(
            name=name,
            internal_id=internal_id,
            reads="1000",
            container="96 well plate",
            container_name="hej",
            rml_plate_name=None,
            well_position=well_position,
            well_position_rml=None,
            sex=None,
            panels=None,
            require_qcok=True,
            application="MWRNXTR003",
            source=None,
            status=None,
            customer="cust015",
            family=None,
            priority="standard",
            capture_kit=None,
            comment="comment",
            index=None,
            reagent_label=None,
            tumour=False,
            custom_index=None,
            elution_buffer="Nuclease-free water",
            organism=organism,
            reference_genome=ref_genomes[organism],
            extraction_method="MagNaPure 96 (contact Clinical Genomics before " "submission)",
            analysis="fastq",
            concentration_weight="1",
            mother=None,
            father=None,
        )
        return item

    order = {
        "customer": "cust000",
        "name": "test order",
        "internal_id": "lims_reference",
        "comment": "test comment",
        "ticket_number": "123456",
        "items": [
            _get_item("Jag", "ms1", "D:5", "C. Jejuni"),
            _get_item("testar", "ms2", "H:5", "M. upium"),
            _get_item("list", "ms3", "A:6", "C. difficile"),
        ],
        "project_type": "microbial",
    }
    return order


@pytest.yield_fixture(scope="function")
def microbial_store(base_store, microbial_submitted_order):
    """Setup a store instance for testing analysis API."""
    customer = base_store.customer(microbial_submitted_order["customer"])

    order = base_store.MicrobialOrder(
        internal_id=microbial_submitted_order["internal_id"],
        name=microbial_submitted_order["name"],
        ticket_number=microbial_submitted_order["ticket_number"],
        comment=microbial_submitted_order["comment"],
        created_at=dt.datetime(2012, 3, 3, 10, 10, 10),
        updated_at=dt.datetime(2012, 3, 3, 10, 10, 10),
        ordered_at=dt.datetime(2012, 3, 3, 10, 10, 10),
    )

    order.customer = customer
    base_store.add(order)

    for sample_data in microbial_submitted_order["items"]:
        application_version = base_store.application(sample_data["application"]).versions[0]
        organism = base_store.Organism(
            internal_id=sample_data["organism"], name=sample_data["organism"]
        )
        base_store.add(organism)
        sample = base_store.add_microbial_sample(
            name=sample_data["name"],
            sex=sample_data["sex"],
            internal_id=sample_data["internal_id"],
            ticket=microbial_submitted_order["ticket_number"],
            reads=sample_data["reads"],
            comment=sample_data["comment"],
            organism=organism,
            priority=sample_data["priority"],
            reference_genome=sample_data["reference_genome"],
            application_version=application_version,
        )
        sample.microbial_order = order
        sample.application_version = application_version
        sample.customer = customer
        sample.organism = organism

        base_store.add(sample)

    base_store.commit()
    yield base_store


@pytest.yield_fixture(scope="function", name="analysis_obj")
def fixture_analysis_obj(analysis_store):
    """Fetch a analysis object from a populated store"""
    return analysis_store.analyses()[0]


@pytest.yield_fixture(scope="function")
def family_obj(analysis_obj):
    """Return a family models object."""
    return analysis_obj.family
