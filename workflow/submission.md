# Sample submission

Samples are generally submitted through the order portal, available after loggin in, at: [clinical.scilifelab.se][portal].

Exceptions currently include:

- microbial samples (Excel order form uploaded to LIMS)

We handle different samples using separate forms (Excel + web). The Excel-based "orderforms" are meant to be filled out manually and uploaded to pre-fill the online form.

- **fastq**: library preparation, sequencing, and FASTQ-delivery of human samples.

    Samples are linked into single-sample dummy families in _cg_ and run through MIP to generate trending QC data and genotypes to enable the genotype concordance comparison (see "Genotype").

- **scout**: same as **fastq** + MIP analysis and upload of variants into Scout.

- **external**: only analysis and upload to Scout of already sequenced samples, delivered as FASTQ-files.

    Samples are added to LIMS but not assigned to any workflow other than delivery and invoicing. However, we currently don't charge a cost for running these analyses.

- **rml**: only sequencing of already prepared libraries and delivery of subsequent FASTQ-files.

    Samples are only added to LIMS, the pools are tracked in _cg_ and they are also the basis for invoiving.

- **microbial**: library preparation, sequencing, and FASTQ-delivery of WGS microbial samples

    We preform an internal QC analysis on the data. Samples are currently added directly to LIMS and not tracked in _cg_.

## Manually adding samples to _status_

It's possible to manually add samples and families to _status_ without interacting with LIMS. This can be helpful when downsampling a sample to multiple read levels.

Start by adding the samples, a mother and son for example:

    :man_technologist: cg add sample --sex male --application WGSPCFC030 cust000 Son
    => happylittlemouse
    :man_technologist: cg add sample --sex female --application WGSPCFC030 cust000 Mother
    => prettybighorse

This will generate a unique "petname" for each sample which we use to reference the samples downstream unless you provide an existing LIMS ID with the `--lims` flag. Next add the family so we can analyze the samples in MIP:

    :man_technologist: cg add family --panel OMIM-AUTO --panel SKD cust000 "Test Run"
    => sadkoala

This will generate another "petname" used as the family ID. Now we are ready to link the samples to the family.

    :man_technologist: cg add relationship --status unaffected sadkoala prettybighorse
    :man_technologist: cg add relationship --status affected --mother prettybighorse sadkoala happylittlemouse

We've now created a new family linked to two samples which will be automatically started when all data is available. We've also setup told the system that "prettybighorse" is the mother of "happylittlemouse" which will be taken into account when running the analysis.

## Samples in the lab

After sample submission, samples are generally tracked in workflows in LIMS. Some information relating to sample status is automatically synced with _status_.

    :stopwatch: rasta:~/servers/crontab/transfer-lims-received.sh
    :stopwatch: rasta:~/servers/crontab/transfer-lims-prepared.sh
    :stopwatch: rasta:~/servers/crontab/transfer-lims-delivered.sh

Samples that are not added to LIMS workflows can be manually updated by going to the [admin interface][clinical-api].

The only feedback back to the lab is provided by scripts that update the number of "missing reads" according to the application of each sample. This information is fetched from the _cgstats_ database.

[portal]: https://clinical.scilifelab.se/
[clinical-api]: https://clinical-api.scilifelab.se/admin/
