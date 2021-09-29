Taxonomic filtration
=====================

This documentation applies to ChEMBL targets.
Targets from other sources do not use the UniProt taxonomy and are handled differently.
For example, the DrugBank protein targets must be filtered using a list of species names.

Targets are restricted to a UniProt taxon, and all taxa underneath it.
The default choice is Euteleostomi (117571), which is appropriate for many *human*-oriented analyses.
You can choose another taxon by passing ``--taxa <ids>``.
For example, ``--taxa 10090,10116`` will restrict to mouse and rat.
For subsets of vertebrata, you can alternatively pass the name of the taxon.
The above example can then be ``--taxa 'Rattus norvegicus,Mus musculus'`.
(A few species also have common names, so you can do ``--taxa rat,mouse``.)

The default, Euteleostomi, diverged 430 megaannum (Ma) ago.
It’s a good choice if you want to approximate humans.
In general, you want to maximize the number of relevant annotations while minimizing the total number of species
to limit the number of unique possibilities in the event that the targets are not collapsable across species.
So, leave out taxa that are likely to have a small number of annotations across a large number of species.
(Of course, in some cases having an annotation from an additional organism can increase the confidence.)

Besides Euteleostomi, some good choices are ``-taxa 40674`` (Mammalia),
``-taxa 32525`` (Theria, 160 Ma),
``--taxa 1437010`` (Boreoeutheria, 85 Ma),
``--taxa 314146`` (Euarchontoglires, 75 Ma)
and ``--taxa 9606`` (Homo sapiens, 300 kiloannum).
Sarcopterygii (under Euteleostomi) won’t include zebrafish, and Euarchonta (under Euarchontoglires) won’t include rodents.
If you enter something outside of Vertebrata (525 Ma), a new set will be downloaded from UniProt and cached.

To find more, explore the hierarchy under:
- https://www.uniprot.org/taxonomy/131567 (cellular species)
- https://www.uniprot.org/taxonomy/10239 (viral species)
