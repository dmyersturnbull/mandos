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
[![Coverage](https://coveralls.io/repos/github/dmyersturnbull/mandos/badge.svg?branch=master&service=github)](https://coveralls.io/github/dmyersturnbull/mandos?branch=master)

A pragmatic tool for cheminformatics and drug discovery.

Example:

```bash
cat "VREFGVBLTWBCJP-UHFFFAOYSA-N" > compounds.txt
mandos search mechanism,activity,atc,trial,predicted compounds.txt
```

It will output a CSV file containing extended data and a simple text file of compound–predicate–object triples:

```
CHEMBL661 (alprazolam)  positive allosteric modulator  CHEMBL2093872 (GABA-A receptor; anion channel)
CHEMBL661 (alprazolam)  activity at                    CHEMBL2093872 (GABA-A receptor; anion channel)
CHEMBL661 (alprazolam)  activity at                    CHEMBL2096986 (Cholecystokinin receptor)
CHEMBL661 (alprazolam)  activity at                    CHEMBL4106143 (BRD4/HDAC1)
CHEMBL661 (alprazolam)  predicted at                   CHEMBL2094116 (Serotonin 3 (5-HT3) receptor)
CHEMBL661 (alprazolam)  predicted at                   CHEMBL4430    (Cytochrome P450 17A1)
CHEMBL661 (alprazolam)  phase-3 trial for              D012559       (Schizophrenia)
CHEMBL661 (alprazolam)  phase-4 trial for              D016584       (Panic Disorder)
CHEMBL661 (alprazolam)  phase-4 trial for              D016584       (Anxiety Disorders)
CHEMBL661 (alprazolam)  has ATC L3 code                N05B          (ANXIOLYTICS)
CHEMBL661 (alprazolam)  has ATC L4 code                N05BA         (Benzodiazepine derivatives)
```

**[See the docs](https://mandos-chem.readthedocs.io/en/latest/)** for more info.


[New issues](https://github.com/dmyersturnbull/mandos/issues) and pull requests are welcome.
Please refer to the [contributing guide](https://github.com/dmyersturnbull/mandos/blob/master/CONTRIBUTING.md).
Generated with [Tyrannosaurus](https://github.com/dmyersturnbull/tyrannosaurus).
