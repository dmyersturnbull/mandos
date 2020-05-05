# Filter-chembl

[![Build status](https://img.shields.io/pypi/status/filter-chembl)](https://pypi.org/project/filter-chembl/)
[![Latest version on PyPi](https://badge.fury.io/py/filter-chembl.svg)](https://pypi.org/project/filter-chembl/)
[![Documentation status](https://readthedocs.org/projects/filter-chembl/badge/?version=latest&style=flat-square)](https://readthedocs.org/projects/filter-chembl/)
[![Travis](https://travis-ci.org/dmyersturnbull/filter-chembl.svg?branch=master)](https://travis-ci.org/dmyersturnbull/filter-chembl)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Filter and merge ChEMBL activity and mechanism of action records into simple, concrete lists.

To install, run `pip install filter-chembl`.
Then run:

```bash
filter-chembl --type=moa,activity --input=inchikey-lines.txt
```

The output will be a tab-separated value file like:
> compound-id	compound-name	predicate	target-id	target-name	target-level	uniprot-id	measurement	pchembl	species	flags	dois
> CHEMBL521	ibuprofen	moa:inhibitor	CHEMBL221	Cyclooxygenase-1	protein	IC50<	7.3		human,mouse	.	10.1016/j.bmcl.2011.04.114
> ...

Targets are listed at the lowest level available (usually single protein).
Records are filtered by species and merged across them via UniProt.


### Building, extending, and contributing

[New issues](https://github.com/dmyersturnbull/filter-chembl/issues) and pull requests are welcome.
Filter-chembl is licensed under the [Apache License, version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
