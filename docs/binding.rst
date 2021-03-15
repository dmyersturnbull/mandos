ChEMBL binding and activity
=======================================

Activity filtration rules
****************************

Here are the full rules used to filter activity annotations:

- DATA VALIDITY COMMENT is not ``Potential missing data``, ``Potential transcription error``, ``Outside typical range``
- ASSAY TYPE is binding and STANDARD RELATION is ``=``, ``<``, or ``<=``
- pCHEMBL is non-null
- pCHEMBL ≥ 7 (modify with ``-pchembl``)
- ASSAY ORGANISM is under the specified taxon
- Assay-to-target relationship
  `confidence score <https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions#what-is-the-confidence-score>`_
  ≥ 4 (modify with ``target-confidence``)

.. tip::

    If you want more stringent selection, try setting ``--pchembl 9``.
    Changing ``-target-confidence`` is less likely to be useful.
    Setting ``-tax 32525`` (Theria, 160 Ma),
    ``--tax 1437010`` (Boreoeutheria, 85 Ma),
    or ``--tax 314146`` (Euarchontoglires, 75 Ma)
    might be useful.
