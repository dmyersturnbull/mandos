# Mandos

[![Version status](https://img.shields.io/pypi/status/mandos)](https://pypi.org/project/mandos)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python version compatibility](https://img.shields.io/pypi/pyversions/mandos)](https://pypi.org/project/mandos)
[![Version on Docker Hub](https://img.shields.io/docker/v/dmyersturnbull/mandos?color=green&label=Docker%20Hub)](https://hub.docker.com/repository/docker/dmyersturnbull/mandos)
[![Version on GitHub](https://img.shields.io/github/v/release/dmyersturnbull/mandos?include_prereleases&label=GitHub)](https://github.com/dmyersturnbull/mandos/releases)
[![Version on PyPi](https://img.shields.io/pypi/v/mandos)](https://pypi.org/project/mandos)
[![Version on Conda-Forge](https://img.shields.io/conda/vn/conda-forge/mandos?label=Conda-Forge)](https://anaconda.org/conda-forge/mandos)  
[![Documentation status](https://readthedocs.org/projects/mandos/badge)](https://mandos.readthedocs.io/en/stable)
[![Build (GitHub Actions)](https://img.shields.io/github/workflow/status/dmyersturnbull/mandos/Build%20&%20test?label=Build%20&%20test)](https://github.com/dmyersturnbull/mandos/actions)
[![Test coverage (coveralls)](https://coveralls.io/repos/github/dmyersturnbull/mandos/badge.svg?branch=main&service=github)](https://coveralls.io/github/dmyersturnbull/mandos?branch=main)
[![Maintainability (Code Climate)](https://api.codeclimate.com/v1/badges/aa7c12d45ad794e45e55/maintainability)](https://codeclimate.com/github/dmyersturnbull/mandos/maintainability)
[![CodeFactor](https://www.codefactor.io/repository/github/dmyersturnbull/mandos/badge)](https://www.codefactor.io/repository/github/dmyersturnbull/mandos)
[![Code Quality (Scrutinizer)](https://scrutinizer-ci.com/g/dmyersturnbull/mandos/badges/quality-score.png?b=main)](https://scrutinizer-ci.com/g/dmyersturnbull/mandos/?branch=main)  
[![Created with Tyrannosaurus](https://img.shields.io/badge/Created_with-Tyrannosaurus-0000ff.svg)](https://github.com/dmyersturnbull/mandos)

A cheminformatics tool that extracts and summarizes knowledge about compounds from 20+ sources.
It then outputs that knowledge in a consistent, human-readable and machine-readable format.

_Status: alpha. The 0.1 release is functional but only used ChEMBL._

### 🎨 Example

Running it on alprazolam:

```bash
echo "VREFGVBLTWBCJP-UHFFFAOYSA-N" > compounds.txt
mandos search compounds.txt --config default
```

You can extensively control the searches by providing a config file (`--config config.toml` instead of default).
**[See the docs 📚](https://mandos-chem.readthedocs.io/en/latest/)** for more info.

It will output one CSV file per search type full of extended information, and a summary CSV file like this one:

```
subj. ID  subj. name  predicate                      obj. ID       obj.name
--------- ----------  -----------------------------  ------------- ------------------------------
CHEMBL661 alprazolam  positive allosteric modulator  CHEMBL2093872 GABA-A receptor; anion channel
CHEMBL661 alprazolam  activity at                    CHEMBL2096986 Cholecystokinin receptor
CHEMBL661 alprazolam  phase-3 trial for              D012559       Schizophrenia
CHEMBL661 alprazolam  phase-4 trial for              D016584       Panic Disorder
CHEMBL661 alprazolam  has ATC L3 code                N05B          anxiolytics
CHEMBL661 alprazolam  has ATC L4 code                N05BA         Benzodiazepine derivatives
PC218     alprazolam  has GHS symbol                 H302          Harmful if swallowed
PC218     alprazolam  has acute effect               -             behavioral: euphoria
PC218     alprazolam  DDI with                       PC65016       amprenavir
PC218     alprazolam  therapeutic for                D001008       Anxiety Disorders
PC218     alprazolam  enriched for term              -             anxiolytic
PC218     alprazolam  co-occurs with drug            PC134664      Benzodiazepine
PC218     alprazolam  co-occurs with gene            1.14.14.1     Monoamine Oxidase
PC218     alprazolam  co-occurs with disease         D016584       Panic Disorder
PC218     alprazolam  interacts with gene            -             CYP3A4
PC218     alprazolam  positive allosteric modulator  GABRA1        GABA(A) Receptor
PC218     alprazolam  inactive at                    KCNMB4        BK Channel
PC218     alprazolam  active at                      AR            androgen receptor
PC218     alprazolam  is of class                    CHEBI:22720   benzodiazepine
PC218     alprazolam  has DEA schedule               4             Schedule IV
.         .             .                              .             .
.         .             .                              .             .
.         .             .                              .             .
```

### 🍁 Contributing

Mandos is licensed under the [Apache License, version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
[New issues](https://github.com/dmyersturnbull/mandos/issues) and pull requests are welcome.
Please refer to the [contributing guide](https://github.com/dmyersturnbull/mandos/blob/master/CONTRIBUTING.md).  
Generated with [Tyrannosaurus](https://github.com/dmyersturnbull/tyrannosaurus).
