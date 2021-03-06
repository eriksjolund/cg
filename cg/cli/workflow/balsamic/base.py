""" Add CLI support to create config and/or start BALSAMIC """
import gzip
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

import click
from cg.apps import hk, lims
from cg.apps.balsamic.fastq import FastqHandler
from cg.utils.fastq import FastqAPI
from cg.cli.workflow.balsamic.store import store as store_cmd
from cg.cli.workflow.balsamic.deliver import deliver as deliver_cmd
from cg.cli.workflow.get_links import get_links
from cg.exc import LimsDataError, BalsamicStartError
from cg.meta.workflow.base import get_target_bed_from_lims
from cg.meta.workflow.balsamic import AnalysisAPI
from cg.store import Store

LOG = logging.getLogger(__name__)
PRIORITY_OPTION = click.option("-p", "--priority", type=click.Choice(["low", "normal", "high"]))
EMAIL_OPTION = click.option("-e", "--email", help="email to send errors to")
SUCCESS = 0
FAIL = 1


@click.group(invoke_without_command=True)
@PRIORITY_OPTION
@EMAIL_OPTION
@click.option("-c", "--case-id", "case_id", help="case to prepare and start an analysis for")
@click.option("--target-bed", required=False, help="Optional")
@click.pass_context
def balsamic(context, case_id, priority, email, target_bed):
    """Cancer workflow """
    context.obj["store_api"] = Store(context.obj["database"])
    context.obj["hk_api"] = hk.HousekeeperAPI(context.obj)
    context.obj["fastq_handler"] = FastqHandler
    context.obj["gzipper"] = gzip
    context.obj["lims_api"] = lims.LimsAPI(context.obj)
    context.obj["fastq_api"] = FastqAPI

    context.obj["analysis_api"] = AnalysisAPI(
        hk_api=context.obj["hk_api"], fastq_api=context.obj["fastq_api"]
    )

    if context.invoked_subcommand is None:
        if case_id is None:
            LOG.error("provide a case")
            context.abort()

        # execute the analysis!
        context.invoke(link, case_id=case_id)
        context.invoke(config_case, case_id=case_id, target_bed=target_bed)
        context.invoke(run, run_analysis=True, case_id=case_id, priority=priority, email=email)


@balsamic.command()
@click.option("-c", "--case", "case_id", help="link all samples for a case")
@click.argument("sample_id", required=False)
@click.pass_context
def link(context, case_id, sample_id):
    """Link FASTQ files for a SAMPLE_ID."""
    store = context.obj["store_api"]
    link_objs = get_links(store, case_id, sample_id)

    for link_obj in link_objs:
        LOG.info(
            "%s: %s link FASTQ files", link_obj.sample.internal_id, link_obj.sample.data_analysis,
        )
        if link_obj.sample.data_analysis and "balsamic" in link_obj.sample.data_analysis.lower():
            LOG.info(
                "%s has balsamic as data analysis, linking.", link_obj.sample.internal_id,
            )
            context.obj["analysis_api"].link_sample(
                fastq_handler=FastqHandler(context.obj),
                case=link_obj.family.internal_id,
                sample=link_obj.sample.internal_id,
            )
        else:
            LOG.warning(
                "%s does not have blasamic as data analysis, skipping.",
                link_obj.sample.internal_id,
            )


@balsamic.command(name="config-case")
@click.option("-d", "--dry-run", "dry", is_flag=True, help="print config to console")
@click.option("--target-bed", required=False, help="Optional")
@click.option("--umi-trim-length", default=5, required=False, help="Default 5")
@click.option("--quality-trim", is_flag=True, required=False, help="Optional")
@click.option("--adapter-trim", is_flag=True, required=False, help="Optional")
@click.option("--umi", is_flag=True, required=False, help="Optional")
@click.argument("case_id")
@click.pass_context
def config_case(
    context, dry, target_bed, umi_trim_length, quality_trim, adapter_trim, umi, case_id
):
    """ Generate a config for the case_id. """

    # missing sample_id and files
    case_obj = context.obj["store_api"].family(case_id)

    if not case_obj:
        LOG.error("Could not find case: %s", case_id)
        context.abort()

    link_objs = case_obj.links
    tumor_paths = set()
    normal_paths = set()
    target_beds = set()
    singularity = context.obj["balsamic"]["singularity"]
    reference_config = context.obj["balsamic"]["reference_config"]
    conda_env = context.obj["balsamic"]["conda_env"]
    root_dir = context.obj["balsamic"]["root"]
    wrk_dir = Path(f"{root_dir}/{case_id}/fastq")
    application_types = set()
    acceptable_applications = {"wgs", "wes", "tgs"}
    applications_requiring_bed = {"wes", "tgs"}

    for link_obj in link_objs:
        LOG.info(
            "%s application type is %s",
            link_obj.sample.internal_id,
            link_obj.sample.application_version.application.prep_category,
        )
        application_types.add(link_obj.sample.application_version.application.prep_category)

        LOG.info("%s: config FASTQ file", link_obj.sample.internal_id)

        linked_reads_paths = {1: [], 2: []}
        concatenated_paths = {1: "", 2: ""}
        file_objs = context.obj["hk_api"].get_files(
            bundle=link_obj.sample.internal_id, tags=["fastq"]
        )
        files = []
        for file_obj in file_objs:
            # figure out flowcell name from header
            with context.obj["gzipper"].open(file_obj.full_path) as handle:
                header_line = handle.readline().decode()
                header_info = context.obj["fastq_api"].parse_header(header_line)
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
        sorted_files = sorted(files, key=lambda k: k["path"])

        for fastq_data in sorted_files:
            original_fastq_path = Path(fastq_data["path"])
            linked_fastq_name = context.obj["fastq_handler"].FastqFileNameCreator.create(
                lane=fastq_data["lane"],
                flowcell=fastq_data["flowcell"],
                sample=link_obj.sample.internal_id,
                read=fastq_data["read"],
                more={"undetermined": fastq_data["undetermined"]},
            )
            concatenated_fastq_name = context.obj[
                "fastq_handler"
            ].FastqFileNameCreator.get_concatenated_name(linked_fastq_name)
            linked_fastq_path = wrk_dir / linked_fastq_name
            linked_reads_paths[fastq_data["read"]].append(linked_fastq_path)
            concatenated_paths[fastq_data["read"]] = f"{wrk_dir}/{concatenated_fastq_name}"

            if linked_fastq_path.exists():
                LOG.info("found: %s -> %s", original_fastq_path, linked_fastq_path)
            else:
                LOG.debug("destination path already exists: %s", linked_fastq_path)

        if link_obj.sample.is_tumour:
            tumor_paths.add(concatenated_paths[1])
        else:
            normal_paths.add(concatenated_paths[1])

        if not target_bed:
            target_bed_filename = get_target_bed_from_lims(
                context.obj["lims_api"], context.obj["store_api"], link_obj.sample.internal_id
            )
            target_beds.add(target_bed_filename)

    if len(application_types) != 1:
        raise BalsamicStartError(
            "More than one application found for this case: %s" % ", ".join(application_types)
        )

    if not application_types.issubset(acceptable_applications):
        raise BalsamicStartError("Improper application for this case: %s" % application_types)

    nr_paths = len(tumor_paths) if tumor_paths else 0
    if nr_paths != 1:
        raise BalsamicStartError("Must have exactly one tumor sample! Found %s samples." % nr_paths)

    tumor_path = tumor_paths.pop()

    normal_path = None
    nr_normal_paths = len(normal_paths) if normal_paths else 0

    if nr_normal_paths == 1:
        normal_path = normal_paths.pop()
    elif nr_normal_paths > 1:
        raise BalsamicStartError("Too many normal samples found: %s" % nr_normal_paths)

    if target_bed and not application_types.issubset(applications_requiring_bed):
        raise BalsamicStartError(
            "--target_bed is incompatible with %s" % " ".join(application_types)
        )

    if not target_bed and application_types.issubset(applications_requiring_bed):
        if len(target_beds) == 1:
            target_bed = Path(context.obj["bed_path"]) / target_beds.pop()
        elif len(target_beds) > 1:
            raise BalsamicStartError("Too many target beds specified: %s" % ", ".join(target_beds))
        else:
            raise BalsamicStartError("No target bed specified!")

    # Call Balsamic
    command_str = (
        f" config case"
        f" --reference-config {reference_config}"
        f" --singularity {singularity}"
        f" --tumor {tumor_path}"
        f" --case-id {case_id}"
        f" --output-config {case_id}.json"
        f" --analysis-dir {root_dir}"
        f" --umi-trim-length {umi_trim_length}"
    )

    if target_bed:
        command_str += f" -p {target_bed}"
    if normal_path:
        command_str += f" --normal {normal_path}"
    if umi:
        command_str += f" --umi"
    if quality_trim:
        command_str += f" --quality-trim"
    if adapter_trim:
        command_str += f" --adapter-trim"
    command = [f"bash -c 'source activate {conda_env}; balsamic"]
    command_str += "'"  # add ending quote from above line
    command.extend(command_str.split(" "))

    if dry:
        LOG.info(" ".join(command))
        return SUCCESS

    process = subprocess.run(" ".join(command), shell=True)
    return process


@balsamic.command()
@click.option("-d", "--dry-run", "dry", is_flag=True, help="print command to console")
@click.option(
    "-r", "--run-analysis", "run_analysis", is_flag=True, default=False, help="start " "analysis",
)
@click.option("--config", "config_path", required=False, help="Optional")
@PRIORITY_OPTION
@EMAIL_OPTION
@click.argument("case_id")
@click.pass_context
def run(context, dry, run_analysis, config_path, priority, email, case_id):
    """Generate a config for the case_id."""

    conda_env = context.obj["balsamic"]["conda_env"]
    slurm_account = context.obj["balsamic"]["slurm"]["account"]
    priority = priority if priority else context.obj["balsamic"]["slurm"]["qos"]
    root_dir = Path(context.obj["balsamic"]["root"])
    if not config_path:
        config_path = Path.joinpath(root_dir, case_id, case_id + ".json")

    # Call Balsamic
    command_str = f" run analysis" f" --account {slurm_account}" f" -s {config_path}"

    if run_analysis:
        command_str += " --run-analysis"

    if email:
        command_str += f" --mail-user {email}"

    command_str += f" --qos {priority}"

    command = [f"bash -c 'source activate {conda_env}; balsamic"]
    command_str += "'"
    command.extend(command_str.split(" "))

    if dry:
        LOG.info(" ".join(command))
        return SUCCESS

    process = subprocess.run(" ".join(command), shell=True)
    return process


@balsamic.command()
@click.option(
    "-d", "--dry-run", "dry_run", is_flag=True, help="print to console without actualising",
)
@click.pass_context
def start(context: click.Context, dry_run):
    """Start all analyses that are ready for analysis."""
    exit_code = SUCCESS
    for case_obj in context.obj["store_api"].cases_to_balsamic_analyze():

        LOG.info("%s: start analysis", case_obj.internal_id)

        priority = get_priority_as_text(case_obj)

        if dry_run:
            continue

        try:
            context.invoke(balsamic, priority=priority, case_id=case_obj.internal_id)
        except LimsDataError as error:
            LOG.exception(error.message)
            exit_code = FAIL

    sys.exit(exit_code)


def get_priority_as_text(case_obj):
    """Get priority as text for a case"""

    if case_obj.high_priority:
        return "high"

    if case_obj.low_priority:
        return "low"

    return "normal"


@balsamic.command("remove-fastq")
@click.option("-c", "--case", "case_id", help="remove fastq folder for a case")
@click.pass_context
def remove_fastq(context, case_id):
    """Remove case fastq folder"""

    wrk_dir = Path(f"{context.obj['balsamic']['root']}/{case_id}/fastq")

    if wrk_dir.exists():
        shutil.rmtree(wrk_dir)


balsamic.add_command(store_cmd)
balsamic.add_command(deliver_cmd)
