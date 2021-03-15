
Target graph traversal
======================

Mandos can collapse ChEMBL binding and mechanism of action annotations within subtypes
of a single target, effectively choosing a broad definition of *target*.

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

In the summarized text file, you may want to collapse annotations across object (target) IDs with the same name.
That way, you won’t have one for mouse, rat, cow, and human.
The full data with all targets is included in the CSV file.

This is what makes mandos pragmatic and useful in more applications:
It’s simpler (read: better) to have a single annotation than 40 (or 160).

*In fact*, Mandos is willing to group and/or *split* targets in nearly arbitrary ways,
as dictated by a dependency-injected `strategy <https://en.wikipedia.org/wiki/Strategy_pattern>`_,
which can also be defined from a specialized file format. Later sections describe the built-in
strategies, file format, and how to craft a totally custom strategy in the Python API.

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
The end result was a dependency-injected `strategy pattern <https://en.wikipedia.org/wiki/Strategy_pattern>`_,
which you can pass to ``mandos chembl:binding`` ``mandos chembl:activity``, and ``mandos chembl:mechanism``
as ``--strategy <name>``.
The default is the null strategy, which does not traverse targets at all; targets are left as-is.

Strategy overview
*****************

There are two main approaches: *grouping* and *splitting*. Grouping tries to walk *up* the graph to get fewer targets,
while *splitting* tries to walk *down* to get single proteins. The latter is less useful for direct analysis and
visualization, but sometimes robust for programmatic analyses.

You can create a custom strategy by subclassing ``TargetTraversalStrategy``.

Specific strategies
*******************

.. warning::

    The following documentation is out-of-date.


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


Strategy format
***************

You can use a custom file format as shown in ``*.strat`` files.
