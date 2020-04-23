"""Tests for cg.cli.store.balsamic"""
import pytest
from cg.cli.workflow.balsamic.store import analysis
from cg.exc import AnalysisDuplicationError

EXIT_SUCCESS = 0


def test_without_options(cli_runner, balsamic_context):
    """Test command with dry option"""

    # GIVEN

    # WHEN dry running without anything specified
    result = cli_runner.invoke(analysis, obj=balsamic_context, catch_exceptions=False)

    # THEN command should mention argument
    assert "Missing argument" in result.output
    assert result.exit_code != EXIT_SUCCESS


def test_store_analysis_with_ok_file_parameter(
    cli_runner, balsamic_store_context, balsamic_case, config_file, deliverables_file
):
    """Test store with analysis file"""

    # GIVEN a meta file for a balsamic analysis

    # WHEN calling store with meta file
    result = cli_runner.invoke(
        analysis,
        [balsamic_case.internal_id, "-c", config_file, "-d", deliverables_file],
        obj=balsamic_store_context,
        catch_exceptions=False,
    )

    # THEN we should not get a message that the analysis has been stored
    assert "included files in Housekeeper" in result.output
    assert result.exit_code == EXIT_SUCCESS


def test_already_stored_analysis(
    cli_runner, balsamic_store_context, balsamic_case, config_file, deliverables_file
):
    """Test store analysis command twice"""

    # GIVEN the analysis has already been stored
    cli_runner.invoke(
        analysis,
        [balsamic_case.internal_id, "-c", config_file, "--deliverables-file", deliverables_file],
        obj=balsamic_store_context,
    )

    # WHEN calling store again for same case
    with pytest.raises(AnalysisDuplicationError):
        result = cli_runner.invoke(
            analysis,
            [
                balsamic_case.internal_id,
                "-c",
                config_file,
                "--deliverables-file",
                deliverables_file,
            ],
            obj=balsamic_store_context,
            catch_exceptions=False,
        )

        # THEN we should get a message that the analysis has previously been stored
        assert "analysis version already added" in result.output
        assert result.exit_code != EXIT_SUCCESS


def test_store_analysis_generates_file_from_directory(
    cli_runner,
    balsamic_store_context,
    balsamic_case,
    config_file,
    deliverables_file_directory,
    mocker,
):
    """Test store with analysis with meta data with one directory"""

    # GIVEN a meta file for a balsamic analysis containing directory that should be included
    mocked_is_dir = mocker.patch("os.path.isdir")
    mocked_is_dir.return_value = True
    mock_make_archive = mocker.patch("shutil.make_archive")
    mock_make_archive.return_value = "file.tar.gz"

    # WHEN calling store with meta file
    result = cli_runner.invoke(
        analysis,
        [
            balsamic_case.internal_id,
            "-c",
            config_file,
            "--deliverables-file",
            deliverables_file_directory,
        ],
        obj=balsamic_store_context,
        catch_exceptions=False,
    )

    # THEN we there should be a file representing the directory in the included bundle
    assert result.exit_code == EXIT_SUCCESS
    assert (
        mock_make_archive.return_value
        in balsamic_store_context["hk_api"].bundle_data["files"][0]["path"]
    )


def test_store_analysis_includes_file_once(
    cli_runner, balsamic_store_context, balsamic_case, config_file, deliverables_file_tags
):
    """Test store with analysis with meta data with same file for multiple tags"""

    # GIVEN a meta file for a balsamic analysis containing one file with two tags

    # WHEN calling store with meta file
    result = cli_runner.invoke(
        analysis,
        [
            balsamic_case.internal_id,
            "-c",
            config_file,
            "--deliverables-file",
            deliverables_file_tags,
        ],
        obj=balsamic_store_context,
        catch_exceptions=False,
    )

    # THEN we there should be one file with two tags in the included bundle
    assert len(balsamic_store_context["hk_api"].bundle_data["files"]) == 1
    assert set(balsamic_store_context["hk_api"].bundle_data["files"][0]["tags"]) == {"vcf", "vep"}
    assert result.exit_code == EXIT_SUCCESS
