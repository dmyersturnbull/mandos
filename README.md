# Mandos

[![Version status](https://img.shields.io/pypi/status/mandos)](https://pypi.org/project/mandos/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/mandos)](https://pypi.org/project/mandos/)
[![Docker](https://img.shields.io/docker/v/dmyersturnbull/mandos?color=green&label=DockerHub)](https://hub.docker.com/repository/docker/dmyersturnbull/mandos)
[![GitHub release (latest SemVer including pre-releases)](https://img.shields.io/github/v/release/dmyersturnbull/mandos?include_prereleases&label=GitHub)](https://github.com/dmyersturnbull/mandos/releases)
[![Latest version on PyPi](https://badge.fury.io/py/mandos.svg)](https://pypi.org/project/mandos/)
[![Documentation status](https://readthedocs.org/projects/mandos-chem/badge/?version=latest&style=flat-square)](https://mandos-chem.readthedocs.io/en/stable/)
[![Build & test](https://github.com/dmyersturnbull/mandos/workflows/Build%20&%20test/badge.svg)](https://github.com/dmyersturnbull/mandos/actions)
[![Maintainability](https://api.codeclimate.com/v1/badges/aa7c12d45ad794e45e55/maintainability)](https://codeclimate.com/github/dmyersturnbull/mandos/maintainability)
[![Coverage](https://coveralls.io/repos/github/dmyersturnbull/mandos/badge.svg?branch=master)](https://coveralls.io/github/dmyersturnbull/mandos?branch=master)

A pragmatic tool for cheminformatics and drug discovery.

Example:

```bash
cat "VREFGVBLTWBCJP-UHFFFAOYSA-N" > compounds.txt
mandos search mechanism,activity,atc,indication,predicted compounds.txt
```

It will output a CSV file containing extended data and a simple text file of compound–predicate–object triples:

```
CHEMBL661 (alprazolam)   positive allosteric modulator   CHEMBL2093872 (GABA-A receptor; anion channel)
CHEMBL661 (alprazolam)   activity at                     CHEMBL2096986 (Cholecystokinin receptor)
CHEMBL661 (alprazolam)   activity at                     CHEMBL4106143 (BRD4/HDAC1)
CHEMBL661 (alprazolam)   predicted at                    CHEMBL2094116 (Serotonin 3 (5-HT3) receptor)
CHEMBL661 (alprazolam)   predicted at                    CHEMBL4430    (Cytochrome P450 17A1)
CHEMBL661 (alprazolam)   indicated for                   D012559       (Schizophrenia)
CHEMBL661 (alprazolam)   indicated for                   D016584       (Panic Disorder)
CHEMBL661 (alprazolam)   has ATC L3 code                 N05B          (ANXIOLYTICS)
CHEMBL661 (alprazolam)   has ATC L4 code                 N05BA         (Benzodiazepine derivatives)
```

[See the docs](https://mandos.readthedocs.io/en/stable/) for more info.


## How does this work?

Annotations are derived from ChEMBL.
First, the compound and its de-salted _parent_ molecule are matched.
ATC codes and MESH indications are taken as-is.

### Target annotation processing

Mechanisms, target activity, and target predictions are handled in a more complex manner.


#### Taxonomic filtration


First, targets are restricted to the specified UniProt taxon.
By default, this is euteleostomi (430 Mya), which is a good choice if you want to approximate humans.
You can choose another taxon by passing `-tax <id>` (or `-tax <name>`, for subsets of vertebrata).
If you enter something outside of vertebrata, a new set will be downloaded from UniProt and cached.

#### Target DAG traversal

Then a directed acyclic graph (DAG) of target supersets is traversed upward, following _SUPERSET_ links
to targets of type _SINGLE PROTEIN_, _PROTEIN FAMILY_, _PROTEIN COMPLEX_, and _PROTEIN COMPLEX GROUP_.

A final target is chosen, preferring _PROTEIN COMPLEX GROUP_, then _PROTEIN COMPLEX_, then _SINGLE PROTEIN_.
This means that _PROTEIN FAMILY_ targets are ignored unless the annotation is actually against one, or
there is a chain `SINGLE PROTEIN ⟶ PROTEIN FAMILY ⟶ PROTEIN COMPLEX`. Both cases are rare at most.

If there are two PROTEIN COMPLEX GROUPs in a chain:
- `SINGLE PROTEIN ⟶ PROTEIN COMPLEX ⟶ PROTEIN COMPLEX GROUP (a) ⟶ PROTEIN COMPLEX GROUP (b)`

Then the higher one (a) will be used. This is similar for branched chains.
For example, (b) will be chosen given these two chains:

- `SINGLE PROTEIN ⟶ PROTEIN COMPLEX ⟶ PROTEIN COMPLEX GROUP (a1) ⟶ PROTEIN COMPLEX GROUP (b)`
- `                                  ⟶ PROTEIN COMPLEX GROUP (a2) ⟶ PROTEIN COMPLEX GROUP (b)`

Occasionally, two or more branched chains will fail to join up. In this case, one annotation will be emitted for each.
For example, both (b1) and (b2) will be used for these:

- `SINGLE PROTEIN ⟶ PROTEIN COMPLEX ⟶ PROTEIN COMPLEX GROUP (a1) ⟶ PROTEIN COMPLEX GROUP (b1)`
- `                                     PROTEIN COMPLEX GROUP (a2) ⟶ PROTEIN COMPLEX GROUP (b2)`

#### Additional filtration

Predicted activity annotations are restricted to Confidence 90% = "active".

Activity annotations are filtered according to:
- no DATA VALIDITY COMMENT
- STANDARD RELATION is `=`, `<`, or `<=`
- ASSAY TYPE is binding
- PCHEMBL is non-null and PCHEMBL >= 7 (or a value from `-pchembl`)
- ASSAY ORGANISM is under the specified taxon (different from the target organism)


[New issues](https://github.com/dmyersturnbull/mandos/issues) and pull requests are welcome.
Please refer to the [contributing guide](https://github.com/dmyersturnbull/mandos/blob/master/CONTRIBUTING.md).
Generated with [Tyrannosaurus](https://github.com/dmyersturnbull/tyrannosaurus).
