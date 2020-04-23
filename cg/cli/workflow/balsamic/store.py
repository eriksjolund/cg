"""Click commands to store balsamic analyses"""

import logging
import os
import subprocess
import sys
from pathlib import Path

import click
from housekeeper.exc import VersionIncludedError

from cg.apps import hk, tb
from cg.meta.store.balsamic import gather_files_and_bundle_in_housekeeper
from cg.store import Store
from cg.exc import AnalysisNotFinishedError, AnalysisDuplicationError, CgError

LOG = logging.getLogger(__name__)
SUCCESS = 0
FAIL = 1


@click.group()
@click.pass_context
def store(context):
    """Store results from MIP in housekeeper."""
    context.obj["db"] = Store(context.obj["database"])
    context.obj["tb_api"] = tb.TrailblazerAPI(context.obj)
    context.obj["hk_api"] = hk.HousekeeperAPI(context.obj)


@store.command()
@click.argument("case_id")
@click.option("-c", "--config", "config_path", required=False, help="Optional")
@click.option(
    "-d", "--deliverables-file", "deliverables_file_path", required=False, help="Optional"
)
@click.pass_context
def analysis(context, case_id, deliverables_file_path, config_path):
    """Store a finished analysis in Housekeeper."""

    status = context.obj["db"]
    case_obj = status.family(case_id)
    root_dir = Path(context.obj["balsamic"]["root"])

    if not case_obj:
        click.echo(click.style(f"Case {case_id} not found", fg="red"))
        context.abort()

    if not deliverables_file_path:
        deliverables_file_path = Path.joinpath(
            root_dir, case_id, "delivery_report", case_id + ".hk"
        )
        if not os.path.isfile(deliverables_file_path):
            context.invoke(generate_deliverables_file, case_id=case_id)

    if not config_path:
        config_path = get_config_path(root_dir, case_id)

    hk_api = context.obj["hk_api"]

    new_analysis = gather_files_and_bundle_in_housekeeper(
        config_path, deliverables_file_path, hk_api, status, case_obj
    )

    status.add_commit(new_analysis)
    click.echo(click.style("included files in Housekeeper", fg="green"))


@store.command("generate-deliverables-file")
@click.option("-d", "--dry-run", "dry", is_flag=True, help="print command to console")
@click.option("--config", "config_path", required=False, help="Optional")
@click.argument("case_id")
@click.pass_context
def generate_deliverables_file(context, dry, config_path, case_id):
    """Generate a deliverables file for the case_id."""

    conda_env = context.obj["balsamic"]["conda_env"]
    root_dir = Path(context.obj["balsamic"]["root"])

    case_obj = context.obj["db"].family(case_id)

    if not case_obj:
        click.echo(click.style(f"Case {case_id} not found", fg="yellow"))

    if not config_path:
        config_path = get_config_path(root_dir, case_id)

    # Call Balsamic
    command_str = f" report deliver" f" --sample-config {config_path}'"

    command = [f"bash -c 'source activate {conda_env}; balsamic"]
    command.extend(command_str.split(" "))

    if dry:
        click.echo(" ".join(command))
        return SUCCESS

    process = subprocess.run(" ".join(command), shell=True)

    if process == SUCCESS:
        click.echo(click.style("created deliverables file", fg="green"))

    return process


def get_config_path(root_dir, case_id):
    return Path.joinpath(root_dir, case_id, case_id + ".json")


@store.command()
@click.pass_context
def completed(context):
    """Store all completed analyses."""
    _store = context.obj["db"]

    exit_code = SUCCESS
    for case in _store.cases_to_balsamic_analyze():
        click.echo(click.style(f"storing case: {case}", fg="blue"))
        try:
            context.invoke(analysis, case_id=case.internal_id)
        except AnalysisNotFinishedError as error:
            click.echo(click.style(error.message, fg="yellow"))
        except FileNotFoundError as error:
            click.echo(click.style(f"missing file: {error.filename}", fg="red"))
            exit_code = FAIL
        except AnalysisDuplicationError:
            click.echo(click.style("analysis version already added", fg="yellow"))
        except VersionIncludedError as error:
            click.echo(click.style(error.message, fg="red"))
            exit_code = FAIL

    sys.exit(exit_code)
