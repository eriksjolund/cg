# cg [![Build Status][travis-image]][travis-url] [![Coverage Status][coveralls-image]][coveralls-url]

`cg` stands for _Clinical Genomics_; a clinical sequencing platform under [SciLifeLab][scilife] 

This is our main package for interacting with data and samples that flow through our pipeline. We rely on a set of specialized "apps" to deal with a lot of complexity like:

- [Trailblazer][trailblazer]: Python wrapper around [MIP][mip], a rare disease genomics pipeline
- [Housekeeper][housekeeper]: storage, retrieval, and archival of files
- [Genotype][genotype]: managing genotypes for detecting sample mix-ups

In this context, `cg` provides the interface between these tools to facilitate automation and other necessary cross-talk. It also exposes some APIs:

- HTTP REST for powering the web portal: [clinical.scilifelab.se][portal]
- CLI for interactions on the command line

## Installation

Cg written in Python 3.6+ and is available on the [Python Package Index][pypi] (PyPI).

```bash
pip install cg
```

If you would like to install the latest development version:

```bash
git clone https://github.com/Clinical-Genomics/cg
cd cg
pip install --editable .
```

For more information, please see the [docs][docs].

[portal]: https://clinical.scilifelab.se/
[trailblazer]: https://github.com/Clinical-Genomics/trailblazer
[trailblazer-ui]: https://trailblazer.scilifelab.se/
[housekeeper]: https://github.com/Clinical-Genomics/housekeeper
[genotype]: https://github.com/Clinical-Genomics/genotype
[mip]: https://github.com/Clinical-Genomics/mip
[scilife]: https://www.scilifelab.se/
[docs]: documentation/README.md

[travis-url]: https://travis-ci.org/Clinical-Genomics/cg
[travis-image]: https://img.shields.io/travis/Clinical-Genomics/cg.svg?style=flat-square

[coveralls-url]: https://coveralls.io/github/Clinical-Genomics/cg
[coveralls-image]: https://coveralls.io/repos/github/Clinical-Genomics/cg/badge.svg?branch=master
