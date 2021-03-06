"""Code that handles CLI commands to upload"""
import datetime as dt
import logging
import sys
import traceback

import click

from cg.apps import coverage as coverage_app
from cg.apps import gt, hk, lims, madeline, scoutapi, tb
from cg.cli.workflow.mip_dna.deliver import CASE_TAGS, SAMPLE_TAGS
from cg.exc import AnalysisUploadError
from cg.meta.deliver import DeliverAPI
from cg.meta.report.api import ReportAPI
from cg.meta.upload.scoutapi import UploadScoutAPI
from cg.meta.workflow.mip_dna import AnalysisAPI
from cg.store import Store

from .beacon import beacon
from .coverage import coverage
from .delivery_report import delivery_report, delivery_report_to_scout, delivery_reports
from .genotype import genotypes
from .mutacc import process_solved, processed_solved
from .observations import observations
from .scout import scout, upload_case_to_scout
from .utils import _suggest_cases_to_upload
from .validate import validate

LOG = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.option("-f", "--family", "family_id", help="Upload to all apps")
@click.option(
    "-r",
    "--restart",
    "force_restart",
    is_flag=True,
    help="Force upload of analysis " "marked as started",
)
@click.pass_context
def upload(context, family_id, force_restart):
    """Upload results from analyses."""

    click.echo(click.style("----------------- UPLOAD ----------------------"))

    context.obj["status"] = Store(context.obj["database"])

    if family_id:
        family_obj = context.obj["status"].family(family_id)
        if not family_obj:
            message = f"family not found: {family_id}"
            click.echo(click.style(message, fg="red"))
            context.abort()

        if not family_obj.analyses:
            message = f"no analysis exists for family: {family_id}"
            click.echo(click.style(message, fg="red"))
            context.abort()

        analysis_obj = family_obj.analyses[0]

        if analysis_obj.uploaded_at is not None:
            message = f"analysis already uploaded: {analysis_obj.uploaded_at.date()}"
            click.echo(click.style(message, fg="red"))
            context.abort()

        if not force_restart and analysis_obj.upload_started_at is not None:
            if dt.datetime.now() - analysis_obj.upload_started_at > dt.timedelta(hours=24):
                raise AnalysisUploadError(
                    f"The upload started at {analysis_obj.upload_started_at} "
                    f"something went wrong, restart it with the --restart flag"
                )

            message = f"analysis upload already started: {analysis_obj.upload_started_at.date()}"
            click.echo(click.style(message, fg="yellow"))
            return

    context.obj["housekeeper_api"] = hk.HousekeeperAPI(context.obj)

    context.obj["madeline_api"] = madeline.api.MadelineAPI(context.obj)
    context.obj["genotype_api"] = gt.GenotypeAPI(context.obj)
    context.obj["lims_api"] = lims.LimsAPI(context.obj)
    context.obj["tb_api"] = tb.TrailblazerAPI(context.obj)
    context.obj["chanjo_api"] = coverage_app.ChanjoAPI(context.obj)
    context.obj["deliver_api"] = DeliverAPI(
        context.obj,
        hk_api=context.obj["housekeeper_api"],
        lims_api=context.obj["lims_api"],
        case_tags=CASE_TAGS,
        sample_tags=SAMPLE_TAGS,
    )
    context.obj["scout_api"] = scoutapi.ScoutAPI(context.obj)
    context.obj["analysis_api"] = AnalysisAPI(
        context.obj,
        hk_api=context.obj["housekeeper_api"],
        scout_api=context.obj["scout_api"],
        tb_api=context.obj["tb_api"],
        lims_api=context.obj["lims_api"],
        deliver_api=context.obj["deliver_api"],
    )
    context.obj["report_api"] = ReportAPI(
        store=context.obj["status"],
        lims_api=context.obj["lims_api"],
        chanjo_api=context.obj["chanjo_api"],
        analysis_api=context.obj["analysis_api"],
        scout_api=context.obj["scout_api"],
    )

    context.obj["scout_upload_api"] = UploadScoutAPI(
        hk_api=context.obj["housekeeper_api"],
        scout_api=context.obj["scout_api"],
        madeline_api=context.obj["madeline_api"],
        analysis_api=context.obj["analysis_api"],
        lims_api=context.obj["lims_api"],
    )

    if context.invoked_subcommand is not None:
        return

    if not family_id:
        _suggest_cases_to_upload(context)
        context.abort()

    family_obj = context.obj["status"].family(family_id)
    analysis_obj = family_obj.analyses[0]
    if analysis_obj.uploaded_at is not None:
        message = f"analysis already uploaded: {analysis_obj.uploaded_at.date()}"
        click.echo(click.style(message, fg="yellow"))
    else:
        analysis_obj.upload_started_at = dt.datetime.now()
        context.obj["status"].commit()
        context.invoke(coverage, re_upload=True, family_id=family_id)
        context.invoke(validate, family_id=family_id)
        context.invoke(genotypes, re_upload=False, family_id=family_id)
        context.invoke(observations, case_id=family_id)
        context.invoke(scout, case_id=family_id)
        analysis_obj.uploaded_at = dt.datetime.now()
        context.obj["status"].commit()
        click.echo(click.style(f"{family_id}: analysis uploaded!", fg="green"))


@upload.command()
@click.pass_context
def auto(context):
    """Upload all completed analyses."""

    click.echo(click.style("----------------- AUTO ------------------------"))

    exit_code = 0
    for analysis_obj in context.obj["status"].analyses_to_upload():

        if analysis_obj.family.analyses[0].uploaded_at is not None:
            LOG.warning(
                "Newer analysis already uploaded for %s, skipping", analysis_obj.family.internal_id
            )
            continue

        internal_id = analysis_obj.family.internal_id
        LOG.info("uploading family: %s", internal_id)
        try:
            context.invoke(upload, family_id=internal_id)
        except Exception:

            LOG.error("uploading family failed: %s", internal_id)
            LOG.error(traceback.format_exc())
            exit_code = 1

    sys.exit(exit_code)


upload.add_command(process_solved)
upload.add_command(processed_solved)
upload.add_command(validate)
upload.add_command(beacon)
upload.add_command(scout)
upload.add_command(upload_case_to_scout)
upload.add_command(observations)
upload.add_command(genotypes)
upload.add_command(coverage)
upload.add_command(delivery_report)
upload.add_command(delivery_reports)
upload.add_command(delivery_report_to_scout)
