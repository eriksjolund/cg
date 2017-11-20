# Tools 🛠

This section will give an overview of different tools and how they fit together.

## Housekeeper 🗂

Stores and tags important files. It groups files in "bundles" and keeps track of "versions" of those bundles.

**GitHub**: [Clinical-Genomics/housekeeper](https://github.com/Clinical-Genomics/housekeeper)

It has two main uses:

1. FASTQ-files stored per sample. The name of each bundle is the internal sample ID. This is either the LIMS ID (original samples) or a "petname" (downsampled samples).

    The bundle collects all FASTQ-files for the sample. Each FASTQ-file is tagged with "fastq" and the name of the flowcell it originated on.

       👨‍💻 cg transfer flowcell FLOWCELL-NAME

    > The "version" concept is not used for these bundles. Only the initial version is relevant.

1. The other type of bundle is named after family ID. These bundles store files from completed analyses (currently only MIP runs).

    Files are added automatically when the analysis is marked completed in _Trailblazer_.

    The version concept is here used to group together results of consecutive analyses of the same family (generally the same samples). The version is identified by the start date of the run.

       ⏱ rasta:~/servers/crontab/store-completed.sh
       👨‍💻 cg store analysis CONFIG-PATH

## Trailblazer 🔍 (TB)

Wraps MIP analysis pipeline and tracks the analyses in a web interface. Makes it possible to easily start MIP within some specific conventions.

- families are stored in ONE root directory defined in the TB config

      ⚙️ root: /mnt/hds/proj/bioinfo/families

> There are more conventions enforced on levels above TB, see _cg_.
>
> It's generally a good idea to remove the "analysis" folder for a family before starting a new run.

There's also a database and web interface for tracking current and historic runs: [trailblazer.scilifelab.se](https://trailblazer.scilifelab.se/). Analyses create logs in different states:

- **pending**: analysis has been initiated but non of the programs have finished. This is used to give feedback that a family has started.

- **running**: analysis has started and will eventually complete or fail.

- **failed**: analysis has errored on one or more steps in the pipeline. We usually investigate the error and make a comment on the log with our findings.

    Analyses can fail on many levels but lastly the results are evaluated for QC metrics including coverage and sex predictions. If the analysis only fails for "analysisrunstatus" you can get an overview by running:

      👨‍💻 trailblazer check FAMILY-ID

- **completed**: analysis is finished without errors.

    You can force an analysis to be logged as **completed** by manually setting the "analysisrunstatus" from "not_finished" to "finished" in the analysis config.

    If a family was previously logged as **failed** we normally "hide" the results from the dashboard in the web interface by clicking "Hide" for the failed log.

- **canceled**: analysis in manually canceled from TB. If you for some reason want to halt an analysis you can use the command line which will send cancel-signals to all SLURM jobs that were launched for the analysis.

      👨‍💻 trailblazer cancel ANALYSIS-RUN-ID

## Genotype 🕵️‍♀️

Compare sample genotypes and manage deviations that could indicate sample mix-up.

We send all _human_ samples for external genotyping, excluding:

- tumour samples => not straight forward to compare concordance
- "focused exome" (or other < exome) panels => doesn't cover enough SNPs

## Chanjo 🐼

Sequencing coverage analysis for clinical purposes. Helps answer the general question of which regions of an exome which is not sufficiently covered.

We generate input for _Chanjo_ by running _Sambamba_ with pre-defined quality filters in MIP.

    ⚙️ completeness levels: 10, 15, 20, 50, 100

Results are uploaded along with data to other tools. Data is visualized in a set of coverage reports that are available from Scout.

## cg: lims 👩‍🔬

We have a common (Python) interface towards our Clarity LIMS. It's largely built ontop of the _genologics_ package. It has many uses including:

- fetching sample data; LIMS ID, UDFs, reception data, delivery date, capture kit etc.
- updating sample data
- sample submission using the `/samples/batch/create` API (not using _genologics_)
- Excel sheet "orderform" parsing

## LoqusDB 👩‍🏫

Observation count database used to store how many times we've seen a variant along with links to the corresponding families they've been called in.

Results are viewable in Scout.

The upload from _cg_ keeps track of which samples have been loaded to avoid adding the same results multiple times.

## Scout 📍

Web interface to analyze VCFs and collaborate on solving rare diseases.

**GitHub**: [Clinical-Genomics/scout](https://github.com/Clinical-Genomics/scout)

**Docs**: [www.clinicalgenomics.se/scout](http://www.clinicalgenomics.se/scout/)

You can access the site on [scout.scilifelab.se][scout]. I recommend that you use [Robo 3T][robo-3t] for connecting to the MongoDB database.

### Research variants

Scout separates variants into "clinical" and "research". Only "clinical" (diagnostic) variants are initially loaded. Users can request upload of "research" (_all_) variants directly in _Scout_. When they do, they also confirm that they have relevant consent. This is marked on the case in the database and the additional variants are uploaded automatically.

    ⏱ rasta:~/servers/crontab/cron-add-research.sh

[scout]: https://scout.scilifelab.se/
[robo-3t]: https://robomongo.org/
