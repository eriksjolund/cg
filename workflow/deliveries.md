# Deliveries

Deliveries happen on different levels and multiple tools need to be updated.

## FASTQ files

This is the standard delivery and should generally proceed on a per-sample basis. When a sample has completed sequencing, the FASTQ-files should be renamed with the customer sample names and copied to the delivery server `caesar`.

## Scout

The upload of completed analyses happens automatically. However, this does not mean the sample(s)/analysis is delivered. It's easiest to look in _Trailblazer_ for completed analyses. Delivered analyses are marked with a comment "delivered / RA".

During the automatic upload, _Chanjo_ is used to validate quality against a coverage threshold based on the "OMIM-AUTO" gene panel.

    👨‍💻 cg upload validate FAMILY-ID

Before answer out an analysis, it's important to check that the upload is good. You do this by accessing the list of clinical SNVs and making sure that thers's mix of inheritance models represented. There should also be compounds listed for some variants. The rank score for the top variants should not be lower than about 15.

## LIMS and SupportSystems

All samples (excluding "external") will go throught the "delivery" step in LIMS. This is where the sample is assigned the official delivery date. After you deliver FASTQ and/or an analysis in Scout you should find the related samples in LIMS and pull them through the "delivery" step. These samples are now ready to be invoiced.

It's also important to communicate this to the customer. This is done by writing a note in the ticket in _SupportSystems_. For sequenced samples you can find a link to the ticket in the [portal][portal]. For re-run requests you might need to manually search for the name of the family/sample in ticket system. If all samples in ticket have been delivered, the ticket should be closed.

## Analysis files

Customers can request individual analysis files to be delivered in addition to the Scout upload. This includes BAM alignments (per sample) and VCF files (both SNV and SV). Since these files are generated using the internal sample IDs, the headers and filenames need to be renamed and either linked to the customer directory on `rasta` (collaborators) or copied to `caesar` (external customers).

Requests like this usually takes place separate from regular deliveries in a new ticket.

[portal]: https://clinical.scilifelab.se/
