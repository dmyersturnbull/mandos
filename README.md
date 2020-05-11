# chembler

[![Docker](https://img.shields.io/docker/v/dmyersturnbull/chembler)](https://hub.docker.com/repository/docker/dmyersturnbull/chembler)
[![Latest version on PyPi](https://badge.fury.io/py/chembler.svg)](https://pypi.org/project/chembler/)
[![Documentation status](https://readthedocs.org/projects/chembler/badge/?version=latest&style=flat-square)](https://chembler.readthedocs.io/en/stable/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Build status](https://img.shields.io/pypi/status/chembler)](https://pypi.org/project/chembler/)
[![Build & test](https://github.com/dmyersturnbull/chembler/workflows/Build%20&%20test/badge.svg)](https://github.com/dmyersturnbull/chembler/actions)


Filter and merge ChEMBL activity and mechanism of action records into simple, concrete lists.

To install, run `pip install chembler`.
Then run:

```bash
chembler --type=moa,activity --input=inchikey-lines.txt
```

The output will be a tab-separated value file like:
> compound-id	compound-name	predicate	target-id	target-name	target-level	uniprot-id	measurement	pchembl	species	flags	dois
> CHEMBL521	ibuprofen	moa:inhibitor	CHEMBL221	Cyclooxygenase-1	protein	IC50<	7.3		human,mouse	.	10.1016/j.bmcl.2011.04.114
> ...

Targets are listed at the lowest level available (usually single protein).
Records are filtered by species and merged across them via UniProt.

[See the docs](https://chembler.readthedocs.io/en/stable/) for more information.


##### Contributing:

[New issues](https://github.com/dmyersturnbull/chembler/issues) and pull requests are welcome.
Please refer to the [contributing guide](https://github.com/dmyersturnbull/chembler/blob/master/CONTRIBUTING.md).
