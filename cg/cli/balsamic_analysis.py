# -*- coding: utf-8 -*-
import logging
import shutil
import sys
from pathlib import Path

import click
from cg.apps import hk, tb, scoutapi, lims
from cg.apps.balsamic.fastq import FastqHandler
from cg.exc import LimsDataError
from cg.meta.balsamic_analysis_api import BalsamicAnalysisAPI
from cg.meta.deliver.api import DeliverAPI
from cg.store import Store

LOG = logging.getLogger(__name__)
PRIORITY_OPTION = click.option('-p', '--priority', type=click.Choice(['low', 'normal', 'high']))
EMAIL_OPTION = click.option('-e', '--email', help='email to send errors to')
START_WITH_PROGRAM = click.option('-sw', '--start-with', help='start balsamic from this program.')


@click.group(invoke_without_command=True)
@PRIORITY_OPTION
@EMAIL_OPTION
@START_WITH_PROGRAM
@click.option('-f', '--case', 'case_id', help='case to prepare and start an analysis for')
@click.pass_context
def balsamic_analysis(context, priority, email, case_id, start_with):
    """Prepare and start a Balsamic analysis for a FAMILY_ID."""
    context.obj['db'] = Store(context.obj['database'])
    hk_api = hk.HousekeeperAPI(context.obj)
    scout_api = scoutapi.ScoutAPI(context.obj)
    lims_api = lims.LimsAPI(context.obj)
    context.obj['tb'] = tb.BalsamicTrailblazerAPI(context.obj)
    deliver = DeliverAPI(context.obj, hk_api=hk_api, lims_api=lims_api)
    balsamic = FastqHandler(context.obj)
    context.obj['api'] = BalsamicAnalysisAPI(
        db=context.obj['db'],
        hk_api=hk_api,
        tb_api=context.obj['tb'],
        scout_api=scout_api,
        lims_api=lims_api,
        deliver_api=deliver,
        fastq_handler=balsamic
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
            context.invoke(balsamic_config, case_id=case_id)
            context.invoke(balsamic_link, case_id=case_id)
            context.invoke(balsamic_panel, case_id=case_id)
            context.invoke(balsamic_start, case_id=case_id, priority=priority, email=email,
                           start_with=start_with)


@balsamic_analysis.command()
@click.option('-d', '--dry', is_flag=True, help='print config to console')
@click.argument('case_id')
@click.pass_context
def balsamic_config(context, dry, case_id):
    """Generate a config for the FAMILY_ID.

    Args:
        dry (Bool): Print config to console
        case_id (Str):

    Returns:
    """
    # Get case meta data
    case_obj = context.obj['db'].family(case_id)
    # Balsamic formated pedigree.yaml config

    config_data = context.obj['api'].config(case_obj)

    # Print to console
    if dry:
        print(config_data)
    else:
        # Write to trailblazer root dir / case_id
        out_path = context.obj['tb'].save_config(config_data)
        LOG.info(f"saved config to: {out_path}")


@balsamic_analysis.command()
@click.option('-f', '--case', 'case_id', help='link all samples for a case')
@click.argument('sample_id', required=False)
@click.pass_context
def balsamic_link(context, case_id, sample_id):
    """Link FASTQ files for a SAMPLE_ID."""
    if case_id and (sample_id is None):
        # link all samples in a case
        case_obj = context.obj['db'].family(case_id)
        link_objs = case_obj.links
    elif sample_id and (case_id is None):
        # link sample in all its families
        sample_obj = context.obj['db'].sample(sample_id)
        link_objs = sample_obj.links
    elif sample_id and case_id:
        # link only one sample in a case
        link_objs = [context.obj['db'].link(case_id, sample_id)]
    else:
        LOG.error('provide case and/or sample')
        context.abort()

    for link_obj in link_objs:
        LOG.info(f"{link_obj.sample.internal_id}: link FASTQ files")
        context.obj['api'].link_sample(link_obj)


@balsamic_analysis.command()
@click.option('-p', '--print', 'print_output', is_flag=True, help='print to console')
@click.argument('case_id')
@click.pass_context
def balsamic_panel(context, print_output, case_id):
    """Write aggregated gene panel file."""
    case_obj = context.obj['db'].family(case_id)
    bed_lines = context.obj['api'].panel(case_obj)
    if print_output:
        for bed_line in bed_lines:
            print(bed_line)
    else:
        context.obj['tb'].write_panel(case_id, bed_lines)


@balsamic_analysis.command()
@PRIORITY_OPTION
@EMAIL_OPTION
@START_WITH_PROGRAM
@click.argument('case_id')
@click.pass_context
def balsamic_start(context: click.Context, case_id: str, priority: str = None, email: str = None,
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


@balsamic_analysis.command()
@click.pass_context
def balsamic_auto(context: click.Context):
    """Start all analyses that are ready for analysis."""
    exit_code = 0
    for case_obj in context.obj['db'].cases_to_balsamic_analyze():
        LOG.info(f"{case_obj.internal_id}: start analysis")
        priority = ('high' if case_obj.high_priority else
                    ('low' if case_obj.low_priority else 'normal'))
        try:
            context.invoke(balsamic_analysis, priority=priority, case_id=case_obj.internal_id)
        except tb.BalsamicStartError as error:
            LOG.exception(error.message)
            exit_code = 1
        except LimsDataError as error:
            LOG.exception(error.message)
            exit_code = 1

    sys.exit(exit_code)


@balsamic_analysis.command()
@click.option('-f', '--case', 'case_id', help='remove fastq folder for a case')
@click.pass_context
def balsamic_rm_fastq(context, case_id):
    """remove fastq folder"""

    wrk_dir = Path(f"{context.obj['balsamic']['root']}/{case_id}/fastq")

    if wrk_dir.exists():
        shutil.rmtree(wrk_dir)
