# -*- coding: utf-8 -*-
import datetime as dt
import logging
import sys
from typing import List

import click
from cg.apps import coverage as coverage_app, gt, hk, loqus, tb, scoutapi, beacon as beacon_app, \
    lims, mutacc_auto
from cg.exc import DuplicateRecordError, DuplicateSampleError
from cg.meta.analysis import AnalysisAPI
from cg.meta.deliver.api import DeliverAPI
from cg.meta.report.api import ReportAPI
from cg.meta.upload.beacon import UploadBeaconApi
from cg.meta.upload.coverage import UploadCoverageApi
from cg.meta.upload.gt import UploadGenotypesAPI
from cg.meta.upload.mutacc import UploadToMutaccAPI
from cg.meta.upload.observations import UploadObservationsAPI
from cg.meta.upload.scoutapi import UploadScoutAPI
from cg.store import Store, models

LOG = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.option('-f', '--family', 'family_id', help='Upload to all apps')
@click.option('-r', '--restart', 'force_restart', is_flag=True, help='Force upload of analysis '
                                                                     'marked as started')
@click.pass_context
def upload(context, family_id, force_restart):
    """Upload results from analyses."""

    click.echo(click.style('----------------- UPLOAD ----------------------'))

    context.obj['status'] = Store(context.obj['database'])

    if family_id:
        family_obj = context.obj['status'].family(family_id)
        if not family_obj:
            message = f"family not found: {family_id}"
            click.echo(click.style(message, fg='red'))
            context.abort()

        if not family_obj.analyses:
            message = f"no analysis exists for family: {family_id}"
            click.echo(click.style(message, fg='red'))
            context.abort()

        analysis_obj = family_obj.analyses[0]

        if analysis_obj.uploaded_at is not None:
            message = f"analysis already uploaded: {analysis_obj.uploaded_at.date()}"
            click.echo(click.style(message, fg='red'))
            context.abort()

        if not force_restart and analysis_obj.upload_started_at is not None:
            if dt.datetime.now() - analysis_obj.upload_started_at > dt.timedelta(hours=24):
                raise Exception(f"The upload started at {analysis_obj.upload_started_at} "
                                f"something went wrong, restart it with the --restart flag")

            message = f"analysis upload already started: {analysis_obj.upload_started_at.date()}"
            click.echo(click.style(message, fg='yellow'))
            return

    context.obj['housekeeper_api'] = hk.HousekeeperAPI(context.obj)

    context.obj['lims_api'] = lims.LimsAPI(context.obj)
    context.obj['tb_api'] = tb.TrailblazerAPI(context.obj)
    context.obj['chanjo_api'] = coverage_app.ChanjoAPI(context.obj)
    context.obj['deliver_api'] = DeliverAPI(context.obj, hk_api=context.obj['housekeeper_api'],
                                            lims_api=context.obj['lims_api'])
    context.obj['scout_api'] = scoutapi.ScoutAPI(context.obj)
    context.obj['analysis_api'] = AnalysisAPI(context.obj, hk_api=context.obj['housekeeper_api'],
                                              scout_api=context.obj['scout_api'],
                                              tb_api=context.obj[
                                                  'tb_api'],
                                              lims_api=context.obj['lims_api'],
                                              deliver_api=context.obj['deliver_api'])
    context.obj['report_api'] = ReportAPI(
        db=context.obj['status'],
        lims_api=context.obj['lims_api'],
        chanjo_api=context.obj['chanjo_api'],
        analysis_api=context.obj['analysis_api'],
        scout_api=context.obj['scout_api']
    )

    context.obj['scout_upload_api'] = UploadScoutAPI(
        status_api=context.obj['status'],
        hk_api=context.obj['housekeeper_api'],
        scout_api=context.obj['scout_api'],
        madeline_exe=context.obj['madeline_exe'],
        analysis_api=context.obj['analysis_api'],
        lims_api=context.obj['lims_api']
    )

    if context.invoked_subcommand is None:
        if not family_id:
            _suggest_cases_to_upload(context)
            context.abort()

        family_obj = context.obj['status'].family(family_id)
        analysis_obj = family_obj.analyses[0]
        if analysis_obj.uploaded_at is not None:
            message = f"analysis already uploaded: {analysis_obj.uploaded_at.date()}"
            click.echo(click.style(message, fg='yellow'))
        else:
            analysis_obj.upload_started_at = dt.datetime.now()
            context.obj['status'].commit()
            context.invoke(coverage, re_upload=True, family_id=family_id)
            context.invoke(validate, family_id=family_id)
            context.invoke(genotypes, re_upload=False, family_id=family_id)
            context.invoke(observations, case_id=family_id)
            context.invoke(scout, case_id=family_id)
            analysis_obj.uploaded_at = dt.datetime.now()
            context.obj['status'].commit()
            click.echo(click.style(f"{family_id}: analysis uploaded!", fg='green'))


@upload.command('delivery-report')
@click.argument('family_id', required=False)
@click.option('-p', '--print', 'print_console', is_flag=True, help='print report to console')
@click.pass_context
def delivery_report(context, family_id, print_console):
    """Generates a delivery report for a case and uploads it to housekeeper and scout

    The report contains data from several sources:

    status-db:
        family
        customer_obj
        application_objs
        accredited
        panels
        samples
        sample.id
        sample.status
        sample.ticket
        sample.million_read_pairs
        sample.prep_date
        sample.received
        sample.sequencing_date
        sample.delivery_date

    lims:
        sample.name
        sample.sex
        sample.source
        sample.application
        sample.prep_method
        sample.sequencing_method
        sample.delivery_method


    trailblazer:
        sample.mapped_reads
        sample.duplicates
        sample.analysis_sex
        mip_version
        genome_build

    chanjo:
        sample.target_coverage
        sample.target_completeness

    scout:
        panel-genes

    calculated:
        today
        sample.processing_time

    """

    click.echo(click.style('----------------- DELIVERY_REPORT -------------'))

    report_api = context.obj['report_api']

    if not family_id:
        _suggest_cases_delivery_report(context)
        context.abort()

    if print_console:
        delivery_report_html = report_api.create_delivery_report(family_id)

        click.echo(delivery_report_html)
    else:
        tb_api = context.obj['tb_api']
        status_api = context.obj['status']
        delivery_report_file = report_api.create_delivery_report_file(family_id,
                                                                      file_path=
                                                                      tb_api.get_family_root_dir(
                                                                          family_id))
        hk_api = context.obj['housekeeper_api']
        added_file = _add_delivery_report_to_hk(delivery_report_file, hk_api, family_id)

        if added_file:
            click.echo(click.style('uploaded to housekeeper', fg='green'))
        else:
            click.echo(click.style('already uploaded to housekeeper, skipping'))

        context.invoke(delivery_report_to_scout, case_id=family_id)
        _update_delivery_report_date(status_api, family_id)


def _add_delivery_report_to_scout(context, path, case_id):
    scout_api = scoutapi.ScoutAPI(context.obj)
    scout_api.upload_delivery_report(path, case_id, update=True)


def _add_delivery_report_to_hk(delivery_report_file, hk_api: hk.HousekeeperAPI, family_id):
    delivery_report_tag_name = 'delivery-report'
    version_obj = hk_api.last_version(family_id)
    uploaded_delivery_report_files = hk_api.get_files(bundle=family_id,
                                                      tags=[delivery_report_tag_name],
                                                      version=version_obj.id)
    number_of_delivery_reports = len(uploaded_delivery_report_files.all())
    is_bundle_missing_delivery_report = number_of_delivery_reports == 0

    if is_bundle_missing_delivery_report:
        file_obj = hk_api.add_file(delivery_report_file.name, version_obj, delivery_report_tag_name)
        hk_api.include_file(file_obj, version_obj)
        hk_api.add_commit(file_obj)
        return file_obj

    return None


def _update_delivery_report_date(status_api, case_id):
    family_obj = status_api.family(case_id)
    analysis_obj = family_obj.analyses[0]
    analysis_obj.delivery_report_created_at = dt.datetime.now()
    status_api.commit()


@upload.command('delivery-report-to-scout')
@click.argument('case_id', required=False)
@click.option('-d', '--dry-run', 'dry_run', is_flag=True, help='run command without uploading to '
                                                               'scout')
@click.pass_context
def delivery_report_to_scout(context, case_id, dry_run):
    """Fetches an delivery-report from housekeeper and uploads it to scout"""

    if not case_id:
        _suggest_cases_delivery_report(context)
        context.abort()

    hk_api = context.obj['housekeeper_api']
    report = _get_delivery_report_from_hk(hk_api, case_id)

    LOG.info("uploading delivery report %s to scout for case: %s", report, case_id)
    if not dry_run:
        _add_delivery_report_to_scout(context, report, case_id)
    click.echo(click.style('uploaded to scout', fg='green'))


def _get_delivery_report_from_hk(hk_api: hk.HousekeeperAPI, family_id):
    delivery_report_tag_name = 'delivery-report'
    version_obj = hk_api.last_version(family_id)
    uploaded_delivery_report_files = hk_api.get_files(bundle=family_id,
                                                      tags=[delivery_report_tag_name],
                                                      version=version_obj.id)

    if uploaded_delivery_report_files.count() == 0:
        raise FileNotFoundError(f"No delivery report was found in housekeeper for {family_id}")

    return uploaded_delivery_report_files[0].full_path


@upload.command('delivery-reports')
@click.option('-p', '--print', 'print_console', is_flag=True, help='print list to console')
@click.pass_context
def delivery_reports(context, print_console):
    """Generate a delivery reports for all cases that need one"""

    click.echo(click.style('----------------- DELIVERY REPORTS ------------------------'))

    for analysis_obj in context.obj['status'].analyses_to_delivery_report():
        LOG.info("uploading delivery report for family: %s", analysis_obj.family.internal_id)
        try:
            context.invoke(delivery_report,
                           family_id=analysis_obj.family.internal_id,
                           print_console=print_console)
        except Exception:
            LOG.error("uploading delivery report failed for family: %s",
                      analysis_obj.family.internal_id)


@upload.command()
@click.option('-r', '--re-upload', is_flag=True, help='re-upload existing analysis')
@click.argument('family_id', required=False)
@click.pass_context
def coverage(context, re_upload, family_id):
    """Upload coverage from an analysis to Chanjo."""

    click.echo(click.style('----------------- COVERAGE --------------------'))

    if not family_id:
        _suggest_cases_to_upload(context)
        context.abort()

    chanjo_api = coverage_app.ChanjoAPI(context.obj)
    family_obj = context.obj['status'].family(family_id)
    api = UploadCoverageApi(context.obj['status'], context.obj['housekeeper_api'], chanjo_api)
    coverage_data = api.data(family_obj.analyses[0])
    api.upload(coverage_data, replace=re_upload)


@upload.command()
@click.option('-r', '--re-upload', is_flag=True, help='re-upload existing analysis')
@click.argument('family_id', required=False)
@click.pass_context
def genotypes(context, re_upload, family_id):
    """Upload genotypes from an analysis to Genotype."""

    click.echo(click.style('----------------- GENOTYPES -------------------'))

    if not family_id:
        _suggest_cases_to_upload(context)
        context.abort()

    tb_api = tb.TrailblazerAPI(context.obj)
    gt_api = gt.GenotypeAPI(context.obj)
    family_obj = context.obj['status'].family(family_id)
    api = UploadGenotypesAPI(context.obj['status'], context.obj['housekeeper_api'], tb_api, gt_api)
    results = api.data(family_obj.analyses[0])
    if results:
        api.upload(results, replace=re_upload)


@upload.command()
@click.option('-c', '--case_id', help='internal case id, leave empty to process all')
@click.option('-l', '--case-limit', type=int, help='maximum number of cases to upload')
@click.option('--dry-run', is_flag=True, help='only print cases to be processed')
@click.pass_context
def observations(context, case_id, case_limit, dry_run):
    """Upload observations from an analysis to LoqusDB."""

    click.echo(click.style('----------------- OBSERVATIONS ----------------'))

    loqus_api = {'wgs': loqus.LoqusdbAPI(context.obj),
                 'wes': loqus.LoqusdbAPI(context.obj, analysis_type='wes')}


    if case_id:
        families_to_upload = [context.obj['status'].family(case_id)]
    else:
        families_to_upload = context.obj['status'].observations_to_upload()

    nr_uploaded = 0
    for family_obj in families_to_upload:

        if case_limit is not None:
            if nr_uploaded >= case_limit:
                LOG.info("Uploaded %d cases, observations upload will now stop", nr_uploaded)
                break

        if not family_obj.customer.loqus_upload:
            LOG.info("%s: %s not whitelisted for upload to loqusdb. Skipping!",
                     family_obj.internal_id, family_obj.customer.internal_id)
            continue

        if not LinkHelper.all_samples_data_analysis(family_obj.links, ['MIP', '', None]):
            LOG.info("%s: has non-MIP data_analysis. Skipping!", family_obj.internal_id)
            continue

        if not LinkHelper.all_samples_are_non_tumour(family_obj.links):
            LOG.info("%s: has tumour samples. Skipping!", family_obj.internal_id)
            continue

        analysis_list = LinkHelper.all_samples_list_analyses(family_obj.links)
        if len(set(analysis_list)) == 1 and analysis_list[0] in ('wes', 'wgs'):
            analysis_type = analysis_list[0]
        else:
            LOG.info("%s: Undetermined analysis type (wes or wgs) or mixed analyses. Skipping!",
                     family_obj.internal_id)
            continue

        if dry_run:
            LOG.info("%s: Would upload observations", family_obj.internal_id)
            continue

        api = UploadObservationsAPI(context.obj['status'], context.obj['housekeeper_api'],
                                    loqus_api[analysis_type])

        try:
            api.process(family_obj.analyses[0])
            LOG.info("%s: observations uploaded!", family_obj.internal_id)
            nr_uploaded += 1
        except (DuplicateRecordError, DuplicateSampleError) as error:
            LOG.info("%s: skipping observations upload: %s", family_obj.internal_id, error.message)
        except FileNotFoundError as error:
            LOG.info("%s: skipping observations upload: %s", family_obj.internal_id, error)


class LinkHelper:
    """Class that helps handle links"""

    @staticmethod
    def all_samples_are_non_tumour(links: List[models.FamilySample]) -> bool:
        """Return True if all samples are non tumour."""
        return all(not link.sample.is_tumour for link in links)

    @staticmethod
    def all_samples_data_analysis(links: List[models.FamilySample], data_anlysis) -> bool:
        """Return True if all samples has the given data_analysis."""
        return all(link.sample.data_analysis in data_anlysis for link in links)

    @staticmethod
    def all_samples_list_analyses(links: List[models.FamilySample]) -> list:
        """Return analysis type for each sample in case"""
        return [link.sample.application_version.application.analysis_type for link in links]


@upload.command()
@click.option('-r', '--re-upload', is_flag=True, help='re-upload existing analysis')
@click.option('-p', '--print', 'print_console', is_flag=True, help='print config values')
@click.argument('case_id', required=False)
@click.pass_context
def scout(context, re_upload, print_console, case_id):
    """Upload variants from analysis to Scout."""

    click.echo(click.style('----------------- SCOUT -----------------------'))

    if not case_id:
        _suggest_cases_to_upload(context)
        context.abort()

    scout_api = context.obj['scout_api']
    tb_api = context.obj['tb_api']

    family_obj = context.obj['status'].family(case_id)
    scout_upload_api = context.obj['scout_upload_api']
    scout_config = scout_upload_api.generate_config(family_obj.analyses[0])

    if print_console:
        click.echo(scout_config)
        return

    file_path = tb_api.get_family_root_dir(case_id) / 'scout_load.yaml'

    if file_path.exists():
        message = "Scout load config %s already exists, you might remove the file and try " \
                  "again, consider that you might also have it in housekeeper" % file_path
        LOG.warning(message)
        context.abort()

    scout_upload_api.save_config_file(scout_config, file_path)
    hk_api = context.obj['housekeeper_api']
    try:
        LOG.info("Upload file to housekeeper: %s", file_path)
        scout_upload_api.add_scout_config_to_hk(file_path, hk_api, case_id)
    except FileExistsError as err:
        LOG.warning("%s, consider removing the file from housekeeper and try again", str(err))
        context.abort()

    scout_api.upload(scout_config, force=re_upload)


@upload.command()
@click.argument('family_id')
@click.option('-p', '--panel', help='Gene panel to filter VCF by', required=True, multiple=True)
@click.option('-out', '--outfile', help='Name of pdf outfile', default=None)
@click.option('-cust', '--customer', help='Name of customer', default="")
@click.option('-qual', '--quality', help='Variant quality threshold', default=20)
@click.option('-ref', '--genome_reference', help='Chromosome build (default=grch37)',
              default="grch37")
@click.pass_context
def beacon(context: click.Context, family_id: str, panel: str, outfile: str, customer: str,
           quality: int, genome_reference: str):
    """Upload variants for affected samples in a family to cgbeacon."""

    click.echo(click.style('----------------- BEACON ----------------------'))

    if outfile:
        outfile += dt.datetime.now().strftime("%Y-%m-%d_%H:%M:%S.pdf")
    api = UploadBeaconApi(
        status=context.obj['status'],
        hk_api=context.obj['housekeeper_api'],
        scout_api=scoutapi.ScoutAPI(context.obj),
        beacon_api=beacon_app.BeaconApi(context.obj),
    )
    api.upload(
        family_id=family_id,
        panel=panel,
        outfile=outfile,
        customer=customer,
        qual=quality,
        reference=genome_reference,
    )


@upload.command()
@click.pass_context
def auto(context):
    """Upload all completed analyses."""

    click.echo(click.style('----------------- AUTO ------------------------'))

    exit_code = 0
    for analysis_obj in context.obj['status'].analyses_to_upload():

        if analysis_obj.family.analyses[0].uploaded_at is not None:
            LOG.warning("Newer analysis already uploaded for %s, skipping",
                        analysis_obj.family.internal_id)
            continue

        LOG.info(f"uploading family: {analysis_obj.family.internal_id}")
        try:
            context.invoke(upload, family_id=analysis_obj.family.internal_id)
        except Exception as e:
            import traceback
            LOG.error(f"uploading family failed: {analysis_obj.family.internal_id}")
            LOG.error(traceback.format_exc())
            exit_code = 1

    sys.exit(exit_code)


@upload.command()
@click.argument('family_id', required=False)
@click.pass_context
def validate(context, family_id):
    """Validate a family of samples."""

    click.echo(click.style('----------------- VALIDATE --------------------'))

    if not family_id:
        _suggest_cases_to_upload(context)
        context.abort()

    family_obj = context.obj['status'].family(family_id)
    chanjo_api = coverage_app.ChanjoAPI(context.obj)
    chanjo_samples = []
    for link_obj in family_obj.links:
        sample_id = link_obj.sample.internal_id
        chanjo_sample = chanjo_api.sample(sample_id)
        if chanjo_sample is None:
            click.echo(click.style(f"upload coverage for {sample_id}", fg='yellow'))
            continue
        chanjo_samples.append(chanjo_sample)
    if chanjo_samples:
        coverage_results = chanjo_api.omim_coverage(chanjo_samples)
        for link_obj in family_obj.links:
            sample_id = link_obj.sample.internal_id
            if sample_id in coverage_results:
                completeness = coverage_results[sample_id]['mean_completeness']
                mean_coverage = coverage_results[sample_id]['mean_coverage']
                click.echo(f"{sample_id}: {mean_coverage:.2f}X - {completeness:.2f}%")
            else:
                click.echo(f"{sample_id}: sample not found in chanjo", color='yellow')


def _suggest_cases_to_upload(context):
    LOG.warning('provide a case, suggestions:')
    records = context.obj['status'].analyses_to_upload()[:50]
    for family_obj in records:
        click.echo(family_obj)


def _suggest_cases_delivery_report(context):
    LOG.error('provide a case, suggestions:')
    records = context.obj['status'].analyses_to_delivery_report()[:50]
    for family_obj in records:
        click.echo(family_obj)


@upload.command('process-solved')
@click.option('-c', '--case-id', help='internal case id, leave empty to process all')
@click.option('-d', '--days-ago', type=int, default=1, help='days since solved')
@click.option('-C', '--customers', type=str, multiple=True, help="Filter on customers")
@click.option('--dry-run', is_flag=True, help='only print cases to be processed')
@click.pass_context
def process_solved(context, case_id, days_ago, customers, dry_run):
    """Process cases with mutacc that has been marked as solved in scout.
    This prepares them to be uploaded to the mutacc database"""

    click.echo(click.style('----------------- PROCESS-SOLVED ----------------'))

    scout_api = context.obj['scout_api']
    mutacc_auto_api = mutacc_auto.MutaccAutoAPI(context.obj)

    mutacc_upload = UploadToMutaccAPI(scout_api=scout_api, mutacc_auto_api=mutacc_auto_api)

    # Get cases to upload into mutacc from scout
    if case_id is not None:
        finished_cases = scout_api.get_cases(finished=True, case_id=case_id)
    elif days_ago is not None:
        finished_cases = scout_api.get_solved_cases(days_ago=days_ago)
    else:
        LOG.info("Please enter option '--case-id' or '--days-ago'")

    number_processed = 0
    for case in finished_cases:

        number_processed += 1
        if customers:
            if case['owner'] not in customers:
                LOG.info("skipping %s: Not valid customer %s", case['_id'], case['owner'])
                continue
        if dry_run:
            LOG.info("Would process case %s with mutacc", case['_id'])
            continue

        LOG.info("Start processing case %s with mutacc", case['_id'])
        mutacc_upload.extract_reads(case)

    if number_processed == 0:
        LOG.info("No cases were solved within the last %s days", days_ago)


@upload.command('processed-solved')
@click.pass_context
def processed_solved(context):
    """Upload solved cases that has been processed by mutacc to the mutacc database"""

    click.echo(click.style('----------------- PROCESSED-SOLVED ----------------'))

    LOG.info("Uploading processed cases by mutacc to the mutacc database")

    mutacc_auto_api = mutacc_auto.MutaccAutoAPI(context.obj)
    mutacc_auto_api.import_reads()
