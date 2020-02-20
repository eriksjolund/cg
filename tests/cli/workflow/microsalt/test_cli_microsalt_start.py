"""This script tests the cli methods to start run microsalt"""
import logging

from cg.cli.workflow.microsalt.base import start

EXIT_SUCCESS = 0


def test_dry(cli_runner, microsalt_context):
    """Test command with --dry option"""

    # GIVEN case-id

    # WHEN dry running
    result = cli_runner.invoke(start, ["--dry-run"], obj=microsalt_context)

    # THEN command should have accepted the option happily
    assert result.exit_code == EXIT_SUCCESS


def test_microsalt_case_included(cli_runner, microsalt_context, microsalt_case, caplog):
    """Test command with a microsalt case"""

    # GIVEN a case that is ready for Balsamic analysis
    #   -> has a sample that is sequenced and has a
    # microsalt data_type
    for link in microsalt_case.links:
        sample = link.sample
        assert sample.sequenced_at
        assert "microsalt" in sample.data_analysis
    assert not microsalt_case.analyses

    # WHEN running command
    with caplog.at_level(logging.INFO):
        result = cli_runner.invoke(start, ["--dry-run"], obj=microsalt_context)

    # THEN command should have printed the case id
    assert result.exit_code == EXIT_SUCCESS
    assert microsalt_case.internal_id in caplog.text


def test_mip_only_case_excluded(cli_runner, microsalt_context, microsalt_case, caplog):
    """Test command with a microsalt case"""

    # GIVEN a case that is ready for Balsamic analysis
    #   -> has a sample that is sequenced and has a
    # microsalt data_type
    for link in mip_case.links:
        sample = link.sample
        assert sample.sequenced_at
        assert "microsalt" not in sample.data_analysis
    assert not mip_case.analyses

    # WHEN running command
    with caplog.at_level(logging.INFO):
        result = cli_runner.invoke(start, ["--dry-run"], obj=microsalt_context)

    # THEN command should not have printed the case id
    assert result.exit_code == EXIT_SUCCESS
    assert mip_case.internal_id not in caplog.text
