Compound preprocessing
======================


Compounds are matched searched in their de-salted, standardized forms using the ``parent`` molecule definitions
from ChEMBL and PubChem. You can disable this in the global settings, though that is not normally recommended.

ChEMBL parent compounds were computed using
the `ChEMBL structure pipeline <https://github.com/chembl/ChEMBL_Structure_Pipeline>`_, which is pretty good.
The PubChem process is a little more opaque.
You may want to pre-process your compounds using the ChEMBL structure pipeline
or `rdkit <https://rdkit.org>`_ sanitization.
Depending on the charge, desalting may result in duplicated structures
(e.g. two anions after removing a single Na⁺). You can deduplicate the structures
by splitting on ``.`` in a SMILES string, then converting back to InChI Keys.
A ``deduplicate`` function in `chemserve <https://github.com/dmyersturnbull/chemserve>`_ does this.
A simple standardization method is just ``Chem.of(inchiorsmiles).desalt().deduplicate()``, which will
also perform rdkit sanitization.
