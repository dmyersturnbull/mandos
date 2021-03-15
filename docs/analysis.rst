Annotation analysis
===================

pCHEMBL values
**************

Predicted activity annotations are always restricted to Confidence 90% = “active”.

For activity annotations,
`pCHEMBL <https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions#what-is-pchembl>`_
are used to filter annotations for the summary file. The pCHEMBL is just
``−log(molar IC50, XC50, EC50, AC50, Ki, Kd, or Potency)``,
so a pCHEMBL ≥ 7 (default) is basically 100 nM or better.

The pCHEMBL used in the summary file is calculated from the product over annotations:

.. math::

    \sigma(E) = \prod_{a \in A} \text{pchembl}(a) / |A|
