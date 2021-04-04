Mandos
====================================

.. toctree::
    binding
    taxa
    traversal
    literature
    misc
    searches
    analysis
    preprocessing
    settings
    :maxdepth: 1


For an input chemical compound, Mandos extracts a wealth of information about its known
classification, disease indications, target activity, etc., and presents that
data in a consistent, highly human-readable and machine-readable form.

Each annotation is a triple of (*compound*, *predicate*, *object*) with additional data.
For example, to describe one of the targets involved in the mechanism of action (MoA) of cocaine::

    cocaine    antagonist of    voltage-gated sodium channel    〈additional data〉

The output for each query (on a set of compounds) is a CSV file with columns *compound*,
*compound ID*,*predicate*, *predicate ID*, *object*, *object ID*, *annotation ID*, and
*source*, plus columns specific to the annotation type (e.g. *IC50*).
It can also perform structural similarity searches to extract annotations for known compounds
that are highly similar to your input compounds.

The main use cases are:
    - To summarize known information about a compound and its biological activity
      in a consistent, computationally tractable form. For consumption by other tools.
    - To identify pharmacological features that distinguish *hits* from non-hits in chemical screens.
    - To cluster hit compounds in any number of *pharmacological spaces*.
      For example, a scatter plot with `UMAP <https://arxiv.org/abs/1802.03426>`_,
      with the compounds colored by a score from the screen.
    - To train and/or evaluate an algorithm that predicts any of these data types.
      For example, to curate a set of known molecular targets.
    - As negative, or *adversarial* controls, to determine whether your results are overly correlated
      with simple measures like pKa, molecular size, or even deposition date.

.. warning::

    Mandos is in an alpha state, and this documentation may not be accurate.


Example usage
#############

Mandos can be called as a Python API, or as a command-line tools.
The command-line tool is called with:

.. code-block::

    mandos 〈type〉 〈compound-list.txt〉

Where ``type`` is the name of an annotation type (source), and ``compound-list.txt``
is just a line-by-line text file of compound InChI Keys.
It can also be a CSV file with additional columns.

For example:

.. code-block::

    mandos chembl:mechanism compounds.txt

The output is a CSV file. Excluding additional columns, the findings can be summarized as:

.. code-block::

    CHEMBL661 (alprazolam)  positive allosteric modulator  CHEMBL2093872 (GABA-A receptor; anion channel)
    ...


Annotation types
################

Currently, all annotations are accessed from one of there primary sources: ChEMBL, DrugBank, or the
Human Metabolome Database (HMDB).
Those from PubChem are mostly derived from other sources, such as DrugBank.
The types are organized either as *chembl:〈type〉*, or as *〈section〉.〈source〉:〈type〉*,
where *section* approximately corresponds to the name of a section on the PubChem webpage for a PubChem *compound*.
For example, see
the `PubChem entry for cocaine <https://pubchem.ncbi.nlm.nih.gov/compound/Cocaine>`_.
One section is called *Pharmacology and Biochemistry*; these are grouped under the *pharma* section in Mandos.

See below for the full list of annotations. Documentation about each of these types can be found by
running ``mandos 〈type〉 --help`` (e.g. ``mandos chembl:go --help``).
The vast majority of these have various parameters and flags. For example, ``chembl:trials`` can filter by the phase
of the trial, and ``chembl:binding`` can filter by the species taxonomy, minimum score, target mapping confidence, etc.
You can pass these with ``--〈param〉 〈value〉`` or ``--flag``.
All parameters have defaults, but they may not be appropriate for a given use case.
More important parameters (such as taxon) are marked as such in the help.

All data fetched from ChEMBL and PubChem are cached under ``~/.mandos``.
This means that if you modify the parameters for a query and re-run, the results should be returned quickly.
For example, if you run ``mandos binding compounds.txt --taxa human``, then
running ``mandos binding compounds.txt --taxa @all`` later will be fast.

Below is the full list of annotation types that are available at the command-line.
More can be found in the Python API; these are generally too specialized to be commonly used.
Some types also warrant dedicated documentation, which can be found in other pages on this site.

.. hint::

    The names of commands are always in the form ``source`` : ``type``, with sub-categories of the
    source or type joined with a ``.``. For example, in ``drug.dea:schedule``, the source
    is ``drug.dea`` and the type is ``schedule``. In ``chembl:go.process``, the source
    is ``chembl`` and the type is ``go.process``.
    You can always run ``mandos --help`` to see the command names.

======================= =============================================================================
 search                  description
======================= =============================================================================
chembl:mechanism        ChEMBL molecular mechanism annotations
chembl:binding          ChEMBL binding activity annotations
chembl:functional       ChEMBL functional activity annotations
chembl:admet            ChEMBL ADMET activity annotations
chembl:atc              ATC codes as listed by ChEMBL
chembl:trials           ChEMBL indication annotations as MESH IDs
chembl:go.function      GO Function terms of ChEMBL targets
chembl:go.process       GO Process terms of ChEMBL targets
chembl:go.component     GO Component terms of ChEMBL targets
summary.ncit:link       Compounds linked from the NCIt summary
chem.pubchem:computed   Computed chemical properties on PubChem
drug.livertox:class     LiverTox drug classes
drug.dea:class          DEA drug classes
drug.dea:schedule       DEA schedules
drug.hsdb:uses          Uses from the HSDB
drug.trials:mesh        MeSH codes from clinicaltrials.gov
pharma.mesh:mesh        MeSH codes listed on PubChem
pharma.atc:atc          ATC codes listed on PubChem
pharma.drugbank:link    Linked compounds in the DrugBank summary
pharma.hsdb:link        Linked compounds in the HSDB summary
pharma.drugbank:moa     Linked compounds in the DrugBank MoA summary
pharma.hsdb:moa         Linked compounds in the HSDB MoA summary
use.cpdat:category      Categories from the Chemical and Product Categories
safety.echa:ghs         GHS hazard codes from the European Chemicals Agency
tox.chemidplus:acute    Names of acute effects from ChemIDplus
tox.chemidplus:ld50     Empirical LD50 by organism from ChemIDplus
disease.ctd:mesh        Associated diseases and disorders from the CTD
lit.pubchem:mesh        MeSH codes from associated PubMed articles
lit.pubchem:chemical    Names of compounds co-occurring in the literature
lit.pubchem:gene        Names of genes co-occurring in the literature
lit.pubchem:disease     Names of diseases co-occurring in the literature
inter.dgidb:gene        Drug–gene interactions from the DGIDB
inter.ctd:gene          Chemical–gene interactions from the CTD
inter.drugbank:target   Protein target names from DrugBank
inter.drugbank:fn       Functions of protein targets from DrugBank
inter.drugbank:pk       Transporters, carriers, and enzymes from DrugBank
inter.drugbank:pk-fn    Functions of PK-related proteins from DrugBank
inter.drugbank:ddi      Drug–drug interactions from DrugBank
inter.pubchem:react     Names of pathways from reactions on PubChem
assay.pubchem:activity  Targets from bioAssay activity on PubChem
hmdb:tissue             Tissues listed on HMDB
hmdb:computed           Computed chemical properties from HMDB
drugbank:dosage         Dosage information from DrugBank
drugbank:metabolite     Names of known metabolites from DrugBank
drugbank:admet          Properties predicted from admetSAR via DrugBank
meta:random             Random values 1...n (with replacement)
======================= =============================================================================
