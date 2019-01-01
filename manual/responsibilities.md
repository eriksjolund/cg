# Responsibilities :scroll:

## Rotating responsibilities

These are the bi-weekly responsibilites that are shared within the team. Current responsibilities are decided on the production meeting.

### Genotype :white_check_mark:

- Track samples to be compared in [genotype.scilifelab.se][genotype]
- Upload new Excel reports when they arrive in _SupportSystems_
- Follow up on missing comparisons for incomplete plates

See more detailed information in the method document in [AMSystems][amsystems] - _1477: Genotyping concordance testing_.

### SupportSystems :hospital:

- Check new tickets assigned to "bioinfo" and delegate to the most relevant team member
- Inquire on status of stale tickets within the team ("Can this one be closed?")

### PDC/Flowcells :vhs:

- Fetch the flowcells [listed as requested][fc-queue] (manually update status to "processing")

## Access

### GitHub: [Clinical-Genomics][gh-clinical] organization

We aim to collect all in-house developed project under this GitHub organization. Generally everyone in the IT/Bioinfo team have access to the full organization - to push to/pull from all repositories. We have been grated an academic license to create unlimited private repositotories. Basically anyone in the "Core" team is an "owner" and can make any edits to the organization.

### Sign off

SciLifeLab IT sometimes asks someone to sign off on e.g. giving sudo access to `hiseq.clinical` and similar requests. This can be authorized by:

- KB
- VW

### HTTP access rules

The following members can update access rules for web services and restart _NGINX_.

- KB
- PG
- EoL

### Google Apps: clinicalgenomics.se

The following memebers can log into the [Google Apps domain][google] and manage _Scout_ user accounts. We use our own "@clinicalgenomics.se" accounts to access the admin dashboard.

- KB
- EOL

### [Binero][binero]

_Binero_ is our domain name registrar. We have registered `clinicalgenomics.se` and a few Genomics Medicine Sweden (GMS) domains with them. They provide an admin interface to manage DNS records and domain forwards. Admins include:

- KB

### [Online Partner][online-partner]

We use _Online Partner_ to handle invoicing for Google Apps accounts (used for logging into Scout). We go via them when we want to we want to add additional slots for "@clinicalgenomics.se" accounts. The contact person is:

- EOL

### [surge.sh][surge]

This is a host for static sites. We use it to [publish this guide][manual]. We've allowed the following users/email accounts to deploy updates to the domain:

- kenny.biliau@scilifelab.se (KB)

### [PyPI][pypi]

We publish quite a few Python packages here. People with access to publish updates:

| Package name  | Owner account |
|---------------|---------------|
| cg            | Kenny.Billiau |
| chanjo        | moonso        |
| genotype      | Kenny.Billiau |
| housekeeper   | Kenny.Billiau |
| scout-browser | moonso        |
| trailblazer   | Kenny.Billiau |

[genotype]: https://genotype.scilifelab.se
[fc-queue]: https://clinical.scilifelab.se/flowcells
[amsystems]: https://jo812.amsystem.com/index.php
[google]: google.com/a/clinicalgenomics.se
[surge]: http://surge.sh/
[manual]: http://clinical-manual.surge.sh/
[online-partner]: http://www.onlinepartner.se/
[pypi]: https://pypi.python.org/pypi
[binero]: https://www.binero.se/
[gh-clinical]: https://github.com/Clinical-Genomics
