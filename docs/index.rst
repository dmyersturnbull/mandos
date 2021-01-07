Mandos
====================================

.. toctree::
    :maxdepth: 1


Mandos is simple cheminformatics tool that extracts and simplifies annotations
for disease indications, drug classifications, target binding activity,
and biological processes of compounds or drugs, using annotations derived from ChEMBL

It is especially useful to:
    - Find known target activity, predicted activity, and predicted biological processes
      for drug leads.
    - Evaluate an algorithm that predicts this type of data.

There is currently a single subcommand:

- ``mandos search <what> <compound-list.txt>``

``compound-list.txt`` is just be a line-by-line text file of compound InChI Keys, SMILES,
or other unique identifiers.

For example:

.. code-block::

    mandos search "mechanism,activity,trial,atc" compounds.txt

Running this will output a CSV file containing raw annotations with extended data.
It will then output a text file with compound–predicate–object triples:

.. code-block::

    CHEMBL661 (alprazolam)  positive allosteric modulator  CHEMBL2093872 (GABA-A receptor; anion channel)
    CHEMBL661 (alprazolam)  activity at                    CHEMBL2096986 (Cholecystokinin receptor)
    CHEMBL661 (alprazolam)  activity at                    CHEMBL4106143 (BRD4/HDAC1)
    CHEMBL661 (alprazolam)  phase-3 trial for              D012559       (Schizophrenia)
    CHEMBL661 (alprazolam)  phase-4 trial for              D016584       (Panic Disorder)
    CHEMBL661 (alprazolam)  has ATC L3 code                N05B          (ANXIOLYTICS)
    CHEMBL661 (alprazolam)  has ATC L4 code                N05BA         (Benzodiazepine derivatives)

.. warning::

    Mandos is in an alpha state, and this documentation may not be accurate.
    In particular, the DrugBank and GO term searches are not supported yet.


The searches are below.
You need a `DrugBank API key <https://docs.drugbank.com/v1/#token-authentication>`_
for DrugBank searches.


============  =====================================================================================
 search        description
============  =====================================================================================
mechanism     All ChEMBL molecular mechanism annotations for proteins under the specified taxon.
moa_updown    ChEMBL MoA using up/down/na for the predicates.
activity      ChEMBL binding activity annotations with several filters.
atc_l2        ATC level-2 codes as listed by ChEMBL.
atc_l3        ATC level-3 codes as listed by ChEMBL.
atc_l4        ATC level-4 codes as listed by ChEMBL.
trial         ChEMBL indication annotations as MESH IDs, with at least phase-3 trials (by default).
go_fn_moa     GO Function terms associated with ChEMBL MoA targets. Traversal strategy = 1.
go_proc_moa   GO Process terms associated with ChEMBL MoA targets. Traversal strategy = 1.
go_comp_moa   GO Component terms associated with ChEMBL MoA targets. Traversal strategy = 1.
go_fn_act     GO Function terms associated with ChEMBL activity targets. Traversal strategy = 1.
go_proc_act   GO Process terms associated with ChEMBL activity targets. Traversal strategy = 1.
go_comp_act   GO Component terms associated with ChEMBL activity targets.
db_ind        All DrugBank indication annotations.
db_target     DrugBank mechanism annotations, optionally requiring “pharmacological action”.
db_enzyme     All DrugBank enzyme annotations.
db_pk         All DrugBank enzyme, carrier, and transporter annotations.
db_trial      DrugBank clinical trial annotations, optionally restricted by purpose and phase.
db_admet      DrugBank ADMET feature annotations, filtered by probability and value.
db_class      Classyfire chemical taxonomy annotations from DrugBank.
db_cat        All DrugBank “drug category” annotations.
db_pathway    All DrugBank “pathway” annotations.
db_legal      DrugBank “legal group” annotations (approved / illicit / investigational).
db_text       Non-trivial words extracted from DrugBank text fields, configurable.
db_org        The affected organism from DrugBank.
db_int        DrugBank interaction annotations, only approved by default.
db_atc        ATC annotations from DrugBank. These are more comprehensive.
db_sideef     Side effect MeSH terms from DrugBank.
cactvs        CACTVS molecular fingerprints from PubChem.
chem_props    Chemical property values from PubChem and ChEMBL (except cactvs).
triples       Uses an already-created triples file. (Useful mainly for running with ``--correlate``.)
self          Each compound has one annotation, itself.
random        Random values in the range 1...n compounds (with replacement).
chembl        Shorthand for all annotations from ChEMBL.
db            Shorthand for all annotations from DrugBank.
============  =====================================================================================


Results are cached under ``~/.mandos``, and Mandos will only search when necessary.


How does this work?
###################

Annotations are derived from ChEMBL, DrugBank, and other sources.
First, the compound and its de-salted ``parent`` molecule are matched.

ATC codes and MESH indications are taken as-is.
Mechanisms, target activity, and target predictions are handled in a more complex manner.


Filtering by organism
*********************


First, targets are restricted to the specified UniProt taxon.
You can choose another taxon by passing ``-tax <id>`` (or ``-tax <name>``,
for subsets of vertebrata).
By default, this is Euteleostomi, which diverged 430 megaannum (Ma) ago.
This is a good choice if you want to approximate humans.

In general, you want to maximize the number of relevant annotations while minimizing the total
number of species to limit the number of unique possibilities in the event that the targets
are not collapsable across species.
So, leave out taxa that are likely to have a small number of annotations across a large
number of species. (Of course, in some cases having an annotation from an additional organism
can increase the confidence.)

Besides Euteleostomi, some good choices are ``-tax 40674`` (Mammalia),
``-tax 32525`` (Theria, 160 Ma),
``--tax 1437010`` (Boreoeutheria, 85 Ma),
``--tax 314146`` (Euarchontoglires, 75 Ma)
and ``--tax 9606`` (Homo sapiens, 300 kiloannum).
Anything below Euteleostomi won’t include zebrafish, and anything under Euarchontoglires
won’t include rodents.
If you enter something outside of Vertebrata (525 Ma), a new set will be downloaded from UniProt and cached.


Collapsing target subtypes
**************************

Mandos collapses annotations within subtypes of a single target,
effectively choosing a broad definition of *target*.

``GABA-A receptor; anion channel`` (CHEMBL2093872) is a good,
albeit pathological exemplar of why this is important.
There are 40 subunit-specific targets underneath in human alone.
Getting annotations listed for ``GABA-A receptor; alpha-3/beta-3/gamma-2`` in one compound
but ``GABA receptor beta-3 subunit`` in another.
For that alprazolam example you’ll also get  ``GABA-A receptor; agonist GABA site`` (CHEMBL2109244)

None of this is likely to be very helpful.
Although there can be important pharmacological differences between the different assemblies,
such a difference in the returned annotations is probably better explained by which
assembly or subtype happened to be tested, rather than by any real difference in pharmacology.

In the summarized text file, you may want to collapse annotations across object (target) IDs
with the same name.
That way, you won’t have one for mouse, rat, cow, and human.
The full data with all targets is included in the CSV file.

This is what makes mandos pragmatic and useful in more applications:
It’s simpler (read: better) to have a single annotation than 40 (or 160).


Target graph traversal
**********************

This describes how targets are collapsed.

ChEMBL has structured relationships between targets.
A target can be a:

- single protein
- protein family
- protein complex
- protein complex group
- selectivity group
- other (nucleic acid, unknown, etc.)

And each relationship can be:

- superset of
- subset of
- overlaps with
- equivalent to

We’ll ignore *overlaps with*, *selectivity group*, and *unknown*.
Relationships are also not uniform across species, even for near-exact orthologs,
and there are some other problems, which we’ll show.
But let’s look at some nice cases first.

If we have an annotation against a target called *Single protein*:

.. mermaid::

   graph BT
        t(Single protein, our target) --> a(Protein complex A)
        t(Single protein, our target) --> b(Protein complex B)
        a --> p(Complex group. Gotcha!)
        b --> p(Complex group. Gotcha!)

That worked out well.
All roads point to the complex group, so we can use that.

Another nice case:

.. mermaid::

   graph BT
        t(Single protein, our target) --> a(Protein family A)
        t(Single protein, our target) --> b(Protein family B)
        a --> b(Protein family B. Gotcha!)

These cases happen. But we might instead have this:

.. mermaid::

   graph BT
        t(Single protein, our target) --> a(Protein complex A)
        t(Single protein, our target) --> b(Protein complex B)
        a --> p1(Complex group A. What?)
        b --> p2(Complex group B. Damn it.)

The issue is, of course, that a single protein can be involved in multiple complexes.
And some of those complexes can be *strange*: heterooligomers that are probably better ignored,
so jumping from a single protein to a complex might be dangerous.
We could split on branches, ultimately using both complexes.
But that fails for our criterion of landing on a small number of simple targets.
We don’t want bizarre targets to show up just because GABA A subunit has been observed in a heterooligomeric assembly
with some miscellaneous GPCR.

In fact, the relationships do not form a tree, or even a `DAG <https://en.wikipedia.org/wiki/Directed_acyclic_graph>`_.
The obvious ways to force this structure into a DAG didn’t work out well,
so we’ll need a more complex algorithm.
The end result was a dependency-injected `strategy pattern <https://en.wikipedia.org/wiki/Strategy_pattern>`_.
The traversal strategy can be set by the config key `mandos.traversal_strategy`.
You can create a custom strategy by subclassing `TargetTraversalStrategy`.
Different default strategies are used for different search types; these are described below.

Strategy 0
----------

This is the null strategy, which does not traverse targets at all;
targets are left as-is.

Strategy 1
----------

This strategy splits on selectivity groups, assuming these are not filtered out.
Each selectivity group is split into its protein families or protein complex groups (using subset relationships).
This is the default for mechanism of action (MoA) search
because some MoA annotations are for selectivity groups.
(This makes sense because exactly which target is involved in a mechanism is sometimes unknown.)

Strategy 2
----------

This is the default strategy for activity annotations.
It’s fairly complex.

Briefly, annotations can be aggregated or split, or both.
Single proteins can be followed to protein complexes only if *subunit* appears as a substring,
and they can be followed to protein families only if it is not a substring.
Complexes can be followed to complex groups along relationship types *subset* and *overlaps with*.
(The latter cases appear surprisingly often; complex to complex group seems like subset-to-superset anyway.)
Complex groups can be followed to other complex groups and families to other families (*subset* only).
This also incorporates strategy 1. Non-protein types are left as-is, if not filtered out.

Strategy 3
----------

This is an extension of Strategy 2 that uses built-in stopping rules designed primarily for neurological targets.

Strategy 4
----------

This strategy requires a text file like the following (which is used for Strategy 2).
Put the path as ``mandos.traversal_strategy``.

    ..code-block::

        single_protein            -> protein_complex         words:"subunit","chain"
        protein_complex           -> protein_complex
        protein_complex           ~~ protein_complex_group
        protein_complex_group     -> protein_complex_group
        protein_family            -> protein_family
        selectivity_group         -> protein_complex_group
        selectivity_group         <- protein_complex_group
        selectivity_group         -> protein_family
        selectivity_group         <- protein_family
        any                       == any




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


Indications / trials
****************************

ChEMBL indication annotations are just the trials conducted, regardless of their result.
This results in some phase 3 annotations that are inconsistent with the actual approvals.
The DrugBank search is better and should include almost everything that the ChEMBL search does.
There’s also a DrugBank clinical trial search (``db_trial``) that should be more equivalent
to the ChEMBL one.


Correlation analysis
****************************
