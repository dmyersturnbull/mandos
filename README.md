# Mandos

[![Version status](https://img.shields.io/pypi/status/mandos?label=status)](https://pypi.org/project/mandos)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python version compatibility](https://img.shields.io/pypi/pyversions/mandos?label=Python)](https://pypi.org/project/mandos)
[![Version on Docker Hub](https://img.shields.io/docker/v/dmyersturnbull/mandos?color=green&label=Docker%20Hub)](https://hub.docker.com/repository/docker/dmyersturnbull/mandos)
[![Version on Github](https://img.shields.io/github/v/release/dmyersturnbull/mandos?include_prereleases&label=GitHub)](https://github.com/dmyersturnbull/mandos/releases)
[![Version on PyPi](https://img.shields.io/pypi/v/mandos?label=PyPi)](https://pypi.org/project/mandos)  
[![Build (Actions)](https://img.shields.io/github/workflow/status/dmyersturnbull/mandos/Build%20&%20test?label=Tests)](https://github.com/dmyersturnbull/mandos/actions)
[![Documentation status](https://readthedocs.org/projects/mandos/badge)](https://mandos.readthedocs.io/en/stable/)
[![Coverage (coveralls)](https://coveralls.io/repos/github/dmyersturnbull/mandos/badge.svg?branch=main&service=github)](https://coveralls.io/github/dmyersturnbull/mandos?branch=main)
[![Maintainability (Code Climate)](https://api.codeclimate.com/v1/badges/aa7c12d45ad794e45e55/maintainability)](https://codeclimate.com/github/dmyersturnbull/mandos/maintainability)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/dmyersturnbull/mandos/badges/quality-score.png?b=main)](https://scrutinizer-ci.com/g/dmyersturnbull/mandos/?branch=main)

A cheminformatics tool that extracts and summarizes knowledge about compounds from 20+ sources.
It then outputs that knowledge in a consistent, human-readable and machine-readable format.

*Status: alpha. The 0.1 release is functional but only used ChEMBL.*

Running it on alprazolam:

```bash
echo "VREFGVBLTWBCJP-UHFFFAOYSA-N" > compounds.txt
mandos search all compounds.txt
```

It will output a CSV file containing extended data, and a simple text file of compound–predicate–object triples.  
Here is a sample of lines in the resulting text file:

```
CHEMBL661 (alprazolam)  positive allosteric modulator  CHEMBL2093872 (GABA-A receptor; anion channel)
CHEMBL661 (alprazolam)  activity at                    CHEMBL2093872 (GABA-A receptor; anion channel)
CHEMBL661 (alprazolam)  activity at                    CHEMBL2096986 (Cholecystokinin receptor)
CHEMBL661 (alprazolam)  activity at                    CHEMBL4106143 (BRD4/HDAC1)
CHEMBL661 (alprazolam)  phase-3 trial for              D012559       (Schizophrenia)
CHEMBL661 (alprazolam)  phase-4 trial for              D016584       (Panic Disorder)
CHEMBL661 (alprazolam)  phase-4 trial for              D016584       (Anxiety Disorders)
CHEMBL661 (alprazolam)  has ATC L3 code                N05B          (ANXIOLYTICS)
CHEMBL661 (alprazolam)  has ATC L4 code                N05BA         (Benzodiazepine derivatives)
PC218     (alprazolam)  links to                       PC119         (GABA)
PC218     (alprazolam)  has GHS symbol                 H302          (Harmful if swallowed)
PC218     (alprazolam)  has acute effect               -             (behavioral: euphoria)
PC218     (alprazolam)  has DDI with                   PC65016       (amprenavir)
PC218     (alprazolam)  has disease marker/moa         D000647       (amnesia)
PC218     (alprazolam)  has disease marker/moa         D000647       (amnesia)
PC218     (alprazolam)  has disease therapeutic        D001008       (Anxiety Disorders)
PC218     (alprazolam)  enriched for lit term          -             (depression)
PC218     (alprazolam)  enriched for lit term          -             (anxiolytic)
PC218     (alprazolam)  has lit drug co-occ with       PC134664      (Benzodiazepine)
PC218     (alprazolam)  has gene drug co-occ with      1.14.14.1     (Monoamine Oxidase)
PC218     (alprazolam)  has disease drug co-occ with   D016584       (Panic Disorder)
PC218     (alprazolam)  interacts with gene            -             (CYP3A4)
PC218     (alprazolam)  positive allosteric modulator  GABRA1        (GABA(A) Receptor)
PC218     (alprazolam)  ligand at                      ALB           (Serum albumin)
PC218     (alprazolam)  has DDI with                   PC657181      (Leuprolide)
PC218     (alprazolam)  inactive at                    KCNMB4        (BK Channel)
PC218     (alprazolam)  active at                      AR            (androgen receptor)
PC218     (alprazolam)  is a                           CHEBI:22720   (benzodiazepine)
PC218     (alprazolam)  is a                           CHEBI:35501   (triazolobenzodiazepine)
D00225    (alprazolam)  is in                          KEGG:1124     (Benzodiazepins)
D00225    (alprazolam)  acts by                        KEGG:GABR     (GABAAR)
D00225    (alprazolam)  affects pathway                KEGG:hsa04727 (GABAergic synapse)
PC218     (alprazolam)  has DEA schedule               4             (Schedule IV)
```

(Note that actual format is tab-delimited.)
**[See the docs](https://mandos-chem.readthedocs.io/en/latest/)** for more info.


### Contributing

Mandos is licensed under the [Apache License, version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
[New issues](https://github.com/dmyersturnbull/mandos/issues) and pull requests are welcome.
Please refer to the [contributing guide](https://github.com/dmyersturnbull/mandos/blob/master/CONTRIBUTING.md).  
Generated with [Tyrannosaurus](https://github.com/dmyersturnbull/tyrannosaurus).
