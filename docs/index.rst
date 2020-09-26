Mandos
====================================

.. toctree::
    :maxdepth: 1


Mandos is simple cheminformatics tool that extracts and simplifies annotations for the
disease indications, drug classifications, target binding activity, and  biological processes of compounds or drugs,
using annotations derived from ChEMBL.

It is especially useful to:
    - Find known target activity, predicted activity, and predicted biological processes for drug leads.
    - Evaluate an algorithm that predicts this type of data.

There is currently a single subcommand:

- ``mandos search <what> <compound-list.txt>``

``compound-list.txt`` is just be a line-by-line text file of compound InChI Keys, SMILES, or other unique identifiers.

For example:

.. code-block::

    mandos search "mechanism,activity,trial,atc" compounds.txt

Running this will output a CSV file containing raw annotations with extended data.
It will then output a text file with compound–predicate–object triples:

.. code-block::

    CHEMBL661 (alprazolam)   positive allosteric modulator   CHEMBL2093872 (GABA-A receptor; anion channel)
    CHEMBL661 (alprazolam)   activity at                     CHEMBL2096986 (Cholecystokinin receptor)
    CHEMBL661 (alprazolam)   activity at                     CHEMBL4106143 (BRD4/HDAC1)
    CHEMBL661 (alprazolam)   phase-3 trial for               D012559       (Schizophrenia)
    CHEMBL661 (alprazolam)   phase-4 trial for               D016584       (Panic Disorder)
    CHEMBL661 (alprazolam)   has ATC L3 code                 N05B          (ANXIOLYTICS)
    CHEMBL661 (alprazolam)   has ATC L4 code                 N05BA         (Benzodiazepine derivatives)

Choices are:

+------------+---------------------------------------------------------------------------------------------------------+
| search     | description                                                                                             |
+============+=========================================================================================================+
| mechanism  | All ChEMBL molecular mechanism annotations for proteins under the specified taxon.                      |
| activity   | ChEMBL binding activity annotations with several filters.                                               |
| atc        | ATC level-3 and level-4 codes as listed by ChEMBL.                                                      |
| trial      | ChEMBL indication annotations as MESH IDs, with at least phase-3 trials (by default).                   |
| prediction | ChEMBL target predictions restricted to specified taxa and with "confidence 90%" as "active".           |
| go_fn      | GO Function terms associated with ChEMBL activity annotations (re-using the filters from "activity".    |
| go_proc    | GO Process terms associated with ChEMBL activity annotations (re-using the filters from "activity".     |
| db_ind     | All DrugBank indication annotations. You need an API key.                                               |
| db_target  | DrugBank mechanism annotations, optionally requiring "pharmacological action". You need an API key.     |
| db_enzyme  | All DrugBank enzyme annotations. You need an API key.                                                   |
| db_pk      | All DrugBank enzyme, carrier, and transporter annotations. You need an API key.                         |
| db_trial   | DrugBank clinical trial annotations, optionally restricted by purpose and phase. You need an API key.   |
| db_admet   | DrugBank ADMET feature annotations, filtered by probability and value. You need an API key.             |
| db_class   | Classyfire chemical taxonomy annotations from DrugBank. You need an API key.                            |
| db_cat     | All DrugBank "drug category" annotations. You need an API key.                                          |
| db_pathway | All DrugBank "pathway" annotations. You need an API key.                                                |
| db_legal   | DrugBank "legal group" annotations (approved / illicit / investigational). You need an API key.         |
| db_text    | Non-trivial words extracted from DrugBank text fields, configurable. You need an API key.               |
| db_org     | The affected organism from DrugBank. You need an API key.                                               |
| db_int     | DrugBank interaction annotations, only approved by default. You need an API key.                        |
| db_atc     | ATC annotations from DrugBank. These are more comprehensive. You need an API key.                       |
| chembl     | Shorthand for all annotations from ChEMBL.                                                              |
| db         | Shorthand for all annotations from DrugBank                                                             |
+------------+---------------------------------------------------------------------------------------------------------+


Results are cached under ``~/.mandos``, and Mandos will only search when necessary.


How does this work?
###################

Annotations are derived from ChEMBL.
First, the compound and its de-salted ``parent`` molecule are matched.

ATC codes and MESH indications are taken as-is.
Mechanisms, target activity, and target predictions are handled in a more complex manner.


Filtering by organism
*********************


First, targets are restricted to the specified UniProt taxon.
You can choose another taxon by passing ``-tax <id>`` (or ``-tax <name>``, for subsets of vertebrata).
By default, this is Euteleostomi (430 megaannum (Ma)), which is a good choice if you want to approximate humans.

In general, you want to maximize the number of relevant annotations while minimizing the total number of species to
limit the number of unique possibilities in the event that the targets are not collapsable across species.
So, leave out taxa that are likely to have a small number of annotations across a large number of species.
(Of course, in some cases having an annotation from an additional organism can increase the confidence.)

Besides Euteleostomi, some good choices are ``-tax 40674`` (Mammalia), ``-tax 32525`` (Theria, 160 Ma),
``--tax 1437010`` (Boreoeutheria, 85 Ma), ``--tax 314146`` (Euarchontoglires, 75 Ma)
and ``--tax 9606`` (Homo sapiens, 300 kiloannum).
Anything below Euteleostomi won't include zebrafish, and anything under Euarchontoglires
won't include rodents.
If you enter something outside of Vertebrata (525 Ma), a new set will be downloaded from UniProt and cached.

Collapsing target subtypes
**************************

Mandos collapses annotations within subtypes of a single target, effectively choosing a broad definition of *target*.

``GABA-A receptor; anion channel`` (CHEMBL2093872) is a good, albeit pathological exemplar of why this is important.
There are 40 subunit-specific targets underneath in human alone.
Getting annotations listed for ``GABA-A receptor; alpha-3/beta-3/gamma-2`` in one compound
but ``GABA receptor beta-3 subunit`` in another.
For that alprazolam example you'll also get  ``GABA-A receptor; agonist GABA site`` (CHEMBL2109244)

None of this is likely to be very helpful.
Although there can be important pharmacological differences between the different assemblies,
such a difference in the returned annotations is probably better explained by which assembly or subtype
happened to be tested, rather than by any real difference in pharmacology.

In the summarized text file, you may want to collapse annotations across object (target) IDs with the same name.
That way, you won't have one for mouse, rat, cow, and human.
The full data with all targets is included in the CSV file.

This is what makes mandos pragmatic and useful in more applications: it's simpler (read: better) to have a single
annotation than 40 (or 160).


Target DAG traversal
********************

Here's how this collapsing works.
A directed acyclic graph (DAG) of target supersets is traversed upward, following ``SUPERSET`` links
to targets of type ``SINGLE PROTEIN``, ``PROTEIN FAMILY``, ``PROTEIN COMPLEX``, and ``PROTEIN COMPLEX GROUP``.

A final target is chosen, preferring ``PROTEIN COMPLEX GROUP``, then ``PROTEIN COMPLEX``, then ``SINGLE PROTEIN``.
This means that ``PROTEIN FAMILY`` targets are ignored unless the annotation is actually against one, or
there is a chain ``SINGLE PROTEIN ⟶ PROTEIN FAMILY ⟶ PROTEIN COMPLEX``. Both cases are rare at most.

If there are two PROTEIN COMPLEX GROUPs in a chain:
- ``SINGLE PROTEIN ⟶ PROTEIN COMPLEX ⟶ PROTEIN COMPLEX GROUP (a) ⟶ PROTEIN COMPLEX GROUP (b)``

Then the higher one (a) will be used. This is similar for branched chains.
For example, (b) will be chosen given these two chains:

- ``SINGLE PROTEIN ⟶ PROTEIN COMPLEX ⟶ PROTEIN COMPLEX GROUP (a1) ⟶ PROTEIN COMPLEX GROUP (b)``
- ``                                  ⟶ PROTEIN COMPLEX GROUP (a2) ⟶ PROTEIN COMPLEX GROUP (b)``

Occasionally, two or more branched chains will fail to join up. In this case, one annotation will be emitted for each.
For example, both (b1) and (b2) will be used for these:

- ``SINGLE PROTEIN ⟶ PROTEIN COMPLEX ⟶ PROTEIN COMPLEX GROUP (a1) ⟶ PROTEIN COMPLEX GROUP (b1)``
- ``                                     PROTEIN COMPLEX GROUP (a2) ⟶ PROTEIN COMPLEX GROUP (b2)``


Activity filtration rules
****************************

Here are the full rules used to filter activity annotations:
- DATA VALIDITY COMMENT is not ``Potential missing data``, ``Potential transcription error``, or ``Outside typical range``.
- ASSAY TYPE is binding and STANDARD RELATION is ``=``, ``<``, or ``<=``
- pCHEMBL is non-null
- pCHEMBL ≥ 7 (only applies to the summary; modify with ``-pchembl``)
- ASSAY ORGANISM is under the specified taxon
- Assay-to-target relationship
  `confidence score <https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions#what-is-the-confidence-score>`_
  ≥ 4 (only applies to the summary; modify with ``target-confidence``)

.. tip::

    If you want more stringent selection, try setting ``--pchembl 9``.
    Changing ``-target-confidence`` is less likely to be useful.
    Setting ``-tax 32525`` (Theria, 160 Ma),
    ``--tax 1437010`` (Boreoeutheria, 85 Ma),
    or ``--tax 314146`` (Euarchontoglires, 75 Ma)
    might be useful.


pCHEMBL values
**************

Predicted activity annotations are always restricted to Confidence 90% = "active".

For activity annotations, `pCHEMBL <https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/chembl-data-questions#what-is-pchembl>`_
are used to filter annotations for the summary file. The pCHEMBL is just ``−log(molar IC50, XC50, EC50, AC50, Ki, Kd, or Potency)``,
so a pCHEMBL ≥ 7 (default) is basically 100 nM or better.

The pCHEMBL used in the summary file is just the product over annotations:

.. math::

    \sigma(E) = \prod_{a \in A} \text{pchembl}(a) / |A|
