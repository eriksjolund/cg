# -*- coding: utf-8 -*-
import logging
import shutil
import sys
from pathlib import Path

import click
from cg.apps import hk, tb, scoutapi, lims
from cg.apps.usalt.fastq import FastqHandler
from cg.exc import LimsDataError
from cg.meta.usalt_analysis_api import UsaltAnalysisAPI
from cg.meta.deliver.api import DeliverAPI
from cg.store import Store

LOG = logging.getLogger(__name__)
PRIORITY_OPTION = click.option('-p', '--priority', type=click.Choice(['low', 'normal', 'high']))
EMAIL_OPTION = click.option('-e', '--email', help='email to send errors to')
START_WITH_PROGRAM = click.option('-sw', '--start-with', help='start usalt from this program.')


@click.group(invoke_without_command=True)
@PRIORITY_OPTION
@EMAIL_OPTION
@START_WITH_PROGRAM
@click.option('-f', '--case', 'case_id', help='case to prepare and start an analysis for')
@click.pass_context
def usalt(context, priority, email, case_id, start_with):
    """Prepare and start a Usalt analysis for a FAMILY_ID."""
    context.obj['db'] = Store(context.obj['database'])
    hk_api = hk.HousekeeperAPI(context.obj)
    scout_api = scoutapi.ScoutAPI(context.obj)
    lims_api = lims.LimsAPI(context.obj)
    context.obj['tb'] = tb.UsaltTrailblazerAPI(context.obj)
    deliver = DeliverAPI(context.obj, hk_api=hk_api, lims_api=lims_api)
    usalt = FastqHandler(context.obj)
    context.obj['api'] = UsaltAnalysisAPI(
        db=context.obj['db'],
        hk_api=hk_api,
        tb_api=context.obj['tb'],
        scout_api=scout_api,
        lims_api=lims_api,
        deliver_api=deliver,
        fastq_handler=usalt
    )

    if context.invoked_subcommand is None:
        if case_id is None:
            LOG.error('provide a case')
            context.abort()

        # check everything is okey
        case_obj = context.obj['db'].family(case_id)
        if case_obj is None:
            LOG.error(f"{case_id} not found")
            context.abort()
        is_ok = context.obj['api'].check(case_obj)
        if not is_ok:
            LOG.warning(f"{case_obj.internal_id}: not ready to start")
            # commit the updates to request flowcells
            context.obj['db'].commit()
        else:
            # execute the analysis!
            context.invoke(config, case_id=case_id)
            context.invoke(link, case_id=case_id)
            context.invoke(panel, case_id=case_id)
            context.invoke(start, case_id=case_id, priority=priority, email=email,
                           start_with=start_with)


@usalt.command()
@click.option('-d', '--dry', is_flag=True, help='print config to console')
@click.argument('case_id')
@click.pass_context
def config(context, dry, case_id):
    """Generate a config for the FAMILY_ID.

    Args:
        dry (Bool): Print config to console
        case_id (Str):

    Returns:
    """
    # Get case meta data
    case_obj = context.obj['db'].family(case_id)
    # Usalt formated pedigree.yaml config

    config_data = context.obj['api'].config(case_obj)

    # Print to console
    if dry:
        print(config_data)
    else:
        # Write to trailblazer root dir / case_id
        out_path = context.obj['tb'].save_config(config_data)
        LOG.info(f"saved config to: {out_path}")


@usalt.command()
@click.option('-o', '--order', 'order_id', help='link all samples for an order')
@click.argument('sample_id', required=False)
@click.pass_context
def link(context, order_id, sample_id):
    """Link FASTQ files for a SAMPLE_ID."""

    if order_id and (sample_id is None):
        # link all samples in a case
        sample_objs = context.obj['db'].microbial_order(order_id).samples
    elif sample_id and (order_id is None):
        # link sample in all its families
        sample_objs = [context.obj['db'].microbial_sample(sample_id)]
    elif sample_id and order_id:
        # link only one sample in a case
        sample_objs = [context.obj['db'].microbial_sample(sample_id)]
    else:
        LOG.error('provide order and/or sample')
        context.abort()

    for sample_obj in sample_objs:
        LOG.info(f"{sample_obj.internal_id}: link FASTQ files")
        context.obj['api'].link_sample(sample_obj)


@usalt.command()
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('case_id')
@click.pass_context
def panel(context, print_output, case_id):
    """Write aggregated gene panel file."""
    case_obj = context.obj['db'].family(case_id)
    bed_lines = context.obj['api'].panel(case_obj)
    if print_output:
        for bed_line in bed_lines:
            print(bed_line)
    else:
        context.obj['tb'].write_panel(case_id, bed_lines)


@usalt.command()
@PRIORITY_OPTION
@EMAIL_OPTION
@START_WITH_PROGRAM
@click.argument('case_id')
@click.pass_context
def start(context: click.Context, case_id: str, priority: str = None, email: str = None,
          start_with: str = None):
    """Start the analysis pipeline for a case."""
    case_obj = context.obj['db'].family(case_id)
    if case_obj is None:
        LOG.error(f"{case_id}: case not found")
        context.abort()
    if context.obj['tb'].analyses(family=case_obj.internal_id, temp=True).first():
        LOG.warning(f"{case_obj.internal_id}: analysis already running")
    else:
        context.obj['api'].start(case_obj, priority=priority, email=email, start_with=start_with)


@usalt.command()
@click.pass_context
def auto(context: click.Context):
    """Start all analyses that are ready for analysis."""
    exit_code = 0
    for case_obj in context.obj['db'].cases_to_usalt_analyze():
        LOG.info(f"{case_obj.internal_id}: start analysis")
        priority = ('high' if case_obj.high_priority else
                    ('low' if case_obj.low_priority else 'normal'))
        try:
            context.invoke(usalt, priority=priority, case_id=case_obj.internal_id)
        except tb.UsaltStartError as error:
            LOG.exception(error.message)
            exit_code = 1
        except LimsDataError as error:
            LOG.exception(error.message)
            exit_code = 1

    sys.exit(exit_code)


@usalt.command()
@click.option('-f', '--case', 'case_id', help='remove fastq folder for a case')
@click.pass_context
def rm_fastq(context, case_id):
    """remove fastq folder"""

    wrk_dir = Path(f"{context.obj['usalt']['root']}/{case_id}/fastq")

    if wrk_dir.exists():
        shutil.rmtree(wrk_dir)
