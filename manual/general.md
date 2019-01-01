# General

## Sample vs. Family

Samples and families are both stored in the _status_ database. A family is the core unit we need to start an analysis in MIP. It's important to understand the distiction that samples are dissconnected from the family, in other words a sample can belong to many family connstallations. Families and samples always belongs to ONE customer but a family is not restricted to include samples from it's own customer.

Each family will be analysed and visualized independently in MIP and Scout. This is often used to store historic uploads when e.g. parents are sequenced to complement a child.

## Application (tag)

Another key concept are the application tags. Each sample (pool for RML orders) are assigned an application tag. This is composed of a three part string like "WGSPCFC030". The application defines what should happen to the sample in both lab and analysis.

- **WGS**: whole genome sequencing
- **PCF**: standard PCR-free library preparation
- **C030**: sequencing of 30X coverage (we guarantee 75% of this)

Most of the derived information is explicity stated in _status_. For example the number of reads to sequence and the "analysis type" used to setup MIP.

> The application is synced in _status_ and LIMS (UDF) and it's important that this is maintained. The application should _only_ be changed in the [portal][portal]!

In fact, each sample/pool is linked to a _version_ of an application. Different "application versions" define differnt prices for the deliverables. The application is used for generating the final invoice.

> How/what to deliver is based on the order type and customer.

[portal]: https://clinical.scilifelab.se/
