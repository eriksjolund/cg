# Tools :hammer:

This section will give an overview of different tools and how they fit together.

There is a landing page with links to web interfaces for apps that provide it. You can reach it on: [clinical.scilifelab.se/apps][portal-apps].

> We are documenting configuration of apps and related services in the private "servers" repo: [Clinical-Genomics/servers][servers].

## cg :basketball:

Wrapper app for all integrated services and tools. You integrated with in mainly using:

- **CLI**: on rasta installed as an alias `cg`

- **Web UI**: [Nuxt.js][nuxt]-based service accessed under [clinical.scilifelab.se][portal]

- **Admin UI**: service accessed under [clinical-api.scilifelab.se][clinical-api]

    Also serves as the REST API for the web UI.

The access to the web apps is controlled by the backing database and more specifically the `user` table. It's shared between "internal" and "customer" users. You can add additional users through the **Admin UI** and the **CLI**.


    cg add user --customer cust000 --admin kenny.billiau@scilifelab.se "Kenny Billiau"

Admin users gain access to the **Admin UI** and elevated access to parts of the **Web UI** and is intended for "internal" users only.

### lims :microscope:

We have a common (Python) interface towards our Clarity LIMS. It's largely built ontop of the _genologics_ package. It has many uses including:

- fetching sample data; LIMS ID, UDFs, reception date, delivery date, capture kit etc.
- updating sample data
- sample submission using the `/samples/batch/create` API (not using _genologics_)
- Excel sheet "orderform" parsing

### invoice :dollar:

Generate and manage invoices.

Invoices are generated per customer and for a list of samples or pools. All data for samples are stored in _status_ samples in pools are fetched from LIMS, however, they are still invoiced per pool.

## Housekeeper (HK) :file_folder:

- **GitHub**: [Clinical-Genomics/housekeeper](https://github.com/Clinical-Genomics/housekeeper)

Stores and tags important files. It groups files in "bundles" and keeps track of "versions" of those bundles.

It has two main uses:

1. FASTQ-files stored per sample. The name of each bundle is the internal sample ID. This is either the LIMS ID (original samples) or a "petname" (downsampled samples).

    The bundle collects all FASTQ-files for the sample. Each FASTQ-file is tagged with "fastq" and the name of the flowcell it originated on.

       cg transfer flowcell FLOWCELL-NAME

    > The "version" concept is not used for these bundles. Only the initial version is relevant.

1. The other type of bundle is named after family ID. These bundles store files from completed analyses (currently only MIP runs).

    Files are added automatically when the analysis is marked completed in _Trailblazer_.

    The version concept is here used to group together results of consecutive analyses of the same family (generally the same samples). The version is identified by the start date of the run.

        cg store analysis CONFIG-PATH

## Trailblazer (TB) :mag:

- **GitHub**: [Clinical-Genomics/trailblazer][trailblazer]

Wraps MIP analysis pipeline and tracks the analyses in a web interface. Makes it possible to easily start MIP within some specific conventions.

- families are stored in ONE root directory defined in the TB config

      root: /path/to/families

> There are more conventions enforced on levels above TB, see _cg_.
>
> It's generally a good idea to remove the "analysis" folder for a family before starting a new run.

There's also a database and web interface for tracking current and historic runs: [trailblazer.scilifelab.se](https://trailblazer.scilifelab.se/). Analyses create logs in different states:

- **pending**: analysis has been initiated but non of the programs have finished. This is used to give feedback that a family has started.

- **running**: analysis has started and will eventually complete or fail.

- **failed**: analysis has errored on one or more steps in the pipeline. We usually investigate the error and make a comment on the log with our findings.

    Analyses can fail on many levels but lastly the results are evaluated for QC metrics including coverage and sex predictions. If the analysis only fails for "analysisrunstatus" you can get an overview by running:

      trailblazer check FAMILY-ID

- **completed**: analysis is finished without errors.

    You can force an analysis to be logged as **completed** by manually setting the "analysisrunstatus" from "not_finished" to "finished" in the analysis config.

    If a family was previously logged as **failed** we normally "hide" the results from the dashboard in the web interface by clicking "Hide" for the failed log.

- **canceled**: analysis in manually canceled from TB. If you for some reason want to halt an analysis you can use the command line which will send cancel-signals to all SLURM jobs that were launched for the analysis.

      trailblazer cancel ANALYSIS-RUN-ID

> _Trailblazer_ will try to pick up the email of the submitter to send errors to from the `$SUDO_USER` environment variable

### Web service

A [Nuxt.js][nuxt]-based web UI and a Flask-based API service. They're updated by running:

    ~/servers/resources/update-trailblazer.sh

## Genotype :white_check_mark: / CR

- **GitHub**: [Clinical-Genomics/genotype][genotype]
- **Method**: _1477: Genotyping concordance testing_

Compare sample genotypes and manage deviations that could indicate sample mix-up.

There's a Flask-based web UI. It's updated by running:

    ~/servers/resources/update-genotype.sh

There's also an alias to the _Genotype_ CLI.

We send all _human_ samples for external genotyping, excluding:

- tumour samples => not straight forward to compare concordance
- "focused exome" (or other < exome) panels => doesn't cover enough SNPs

## Chanjo :panda_face:

- **GitHub**: [Clinical-Genomics/chanjo](https://github.com/clinical-genomics/chanjo)
- **GitHub**: [Clinical-Genomics/chanjo-report](https://github.com/clinical-genomics/chanjo-report)

Sequencing coverage analysis for clinical purposes. Helps answer the general question of which regions of an exome which is not sufficiently covered.

We generate input for _Chanjo_ by running _Sambamba_ with pre-defined quality filters in MIP.

    completeness levels: 10, 15, 20, 50, 100

Results are uploaded along with data to other tools. Data is visualized in a set of coverage reports that are available from _Scout_.

_Chanjo_ is available as a CLI under the alias `chanjo`.

_Chanjo_ is used as part of MIP to determine sample sex based on coverage across the X and Y chromosomes. You can run that command yourself as:

    chanjo sex BAM-PATH

To upload results from _Sambamba_ manually you would run:

    chanjo load --group FAMILY-ID --group-name FAMILY-NAME --name SAMPLE-NAME COVERAGE-BED-PATH

### Chanjo-Report

_Chanjo-Report_ can produce HTML/PDF coverage reports. This plugin is integrated in _Scout_ and this is the easiest way to access the coverage results for uploaded cases.

## LoqusDB :bookmark_tabs:

- **GitHub**: [moonso/loqusdb](https://github.com/clinical-genomics/loqusdb)

Observation count database used to store how many times we've seen a variant along with links to the corresponding families they've been called in.

Results are viewable in Scout.

The upload from _cg_ keeps track of which samples have been loaded to avoid adding the same results multiple times.

## Scout :round_pushpin: / MM

- **GitHub**: [Clinical-Genomics/scout](https://github.com/Clinical-Genomics/scout)
- **Docs**: [www.clinicalgenomics.se/scout](http://www.clinicalgenomics.se/scout/)

Web interface to analyze VCFs and collaborate on solving rare diseases.

You can access the site on [scout.scilifelab.se][scout]. I recommend that you use [Robo 3T][robo-3t] for connecting to the MongoDB database.

The service is updated by running:

    ~/servers/resources/update-scout.sh

### Research variants

Scout separates variants into "clinical" and "research". Only "clinical" (diagnostic) variants are initially loaded. Users can request upload of "research" (_all_) variants directly in _Scout_. When they do, they also confirm that they have relevant consent. This is marked on the case in the database and the additional variants are uploaded automatically.

    @ rasta:~/servers/crontab/cron-add-research.sh

[scout]: https://scout.scilifelab.se/
[robo-3t]: https://robomongo.org/
[nuxt]: https://nuxtjs.org/
[portal]: https://clinical.scilifelab.se/
[clinical-api]: https://clinical-api.scilifelab.se/admin/
[portal-apps]: https://clinical.scilifelab.se/apps
[servers]: https://github.com/Clinical-Genomics/servers
[amsystems]: https://jo812.amsystem.com/index.php
[genotype]: https://github.com/Clinical-Genomics/genotype
[trailblazer]: https://github.com/Clinical-Genomics/trailblazer
