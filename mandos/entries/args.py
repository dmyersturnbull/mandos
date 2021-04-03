from inspect import cleandoc as doc
from pathlib import Path
from typing import Mapping, Optional

import typer

from mandos.model.chembl_support import DataValidityComment
from mandos.model.chembl_support.chembl_targets import TargetType, ConfidenceLevel
from mandos.search.chembl.target_traversal import TargetTraversalStrategies


def _stringify(keys: Mapping[str, str]):
    return ", ".join((k if v is None else f"{k} ({v.lower()})" for k, v in keys.items()))


class EntryArgs:

    path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help=doc(
            """
            The path to the input file.
            One of:

              (A) *.txt, *.lines, or *.list (optionally with .gz/.zip/.xz/.bz2)), with one InChI Key per line;

              (B) A *.csv, *.tsv, *.tab file (or .gz/.zip/.xz/.bz2 variant) with a column called 'inchikey'; OR

              (C) An Arrow *.feather file or Parquet *.snappy file with a column called 'inchikey'
        """
        ),
    )

    to = typer.Option(
        None,
        show_default=False,
        help=doc(
            """
            The path to the output file.
            If not set, chooses <input-path>-<search>.csv.gz
            The filename extension should be one of: .csv, .tsv, .tab, .json (with optional .gz/.bz2/.zip/.xz);
            .feather; .snappy (or .parquet); or .h5.
            Feather (.feather), Parquet (.snappy), and tab-delimited (.tsv.gz) are recommended.
            If H5, will add a new dataset named <key> to any existing archive.
            Will fail if the file exists unless the `--overwrite` flag is set.

            If only the filename extension is provided (e.g. --to '.feather'), will only change the output format
            (and filename extension).
        """
        ),
    )

    replace: bool = typer.Option(False, help="Replace output file if they exist. See also: --skip")

    skip: bool = typer.Option(
        False, help="Skip any search if the output file exists (only warns). See also: --replace"
    )

    in_cache: bool = typer.Option(
        False,
        help="Do not download any data. Fails if the needed data is not cached.",
        hidden=True,
    )

    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Configure logger to output INFO (use ``--quiet`` for less info)",
    )

    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Configure logger to output only ERROR (use ``--verbose`` for more info)",
    )

    log_path: Optional[Path] = typer.Option(
        None,
        "--log",
        help="""
            Also log to a file.
            The suffix can be .log, .log.gz, .log.zip, or .json, .json.gz, or .json.gz.
            You can prefix the path with :LEVEL: to control the level. For example, :INFO:out.log
        """,
    )

    no_setup: bool = typer.Option(
        False,
        "--no-setup",
        hidden=True,
        help="Skip setup, such as configuring logging.",
    )

    @staticmethod
    def key(name: str) -> typer.Option:
        return typer.Option(
            name,
            min=1,
            max=120,
            help="""
            A free-text unique key for the search.
            Should be a short, <60-character name that describes the search and any parameters.
            The output file will be named according to a 'sanitized' variant of this value.
            """,
        )

    test = typer.Option(
        False,
        "--check",
        help="Do not run searches; just check that the parameters are ok.",
    )

    taxa = typer.Option(
        "7742",
        show_default=False,
        help=doc(
            """
        The IDs or names of UniProt taxa, comma-separated.
        Taxon names and common names can be used for vertebrate species (where available).

        This can have a significant effect on searches. See the docs for more info.

        [default: 7742] (Euteleostomi)
        """
        ),
    )

    atc_level = typer.Option(
        "1,2,3,4", min=1, max=4, help="""List of ATC levels, comma-separated."""
    )

    min_cooccurrence_score = typer.Option(
        0.0,
        help="Minimum enrichment score, inclusive. See docs for more info.",
        min=0.0,
    )

    min_cooccurring_articles = typer.Option(
        0,
        help="Minimum number of articles for both the compound and object, inclusive.",
        min=0,
    )

    name_must_match = typer.Option(
        False,
        help=doc(
            """
        Require that the name of the compound(s) exactly matches the compound name on PubChem (case-insensitive)
        """
        ),
    )

    acute_effect_level = typer.Option(
        2,
        min=1,
        max=2,
        help="""
      The level in the ChemIDPlus hierarchy of effect names.
      Level 1: e.g. 'behavioral'
      Level 2: 'behavioral: excitement'
      """,
    )

    traversal_strategy = typer.Option(
        "@null",
        "--traversal",
        show_default=False,
        help=doc(
            """
        Target traversal strategy name, file, or class.
        Dictates the way the network of ChEMBL targets is traversed (from the annotated target as a source).
        Specifies the network links that are followed and which targets are 'accepted' for final annotations.
        This option has a dramatic effect on the search. See the docs for more info.

        Can be one of:
        (A) A standard strategy name, starting with @;
        (B) The path to a ``*.strat`` file; OR
        (C) The fully qualified name of a ``TargetTraversal``

        The standard traversal strategies are: {}

        [default: @null] (No traversal; targets as-is)
        """.format(
                "; ".join(TargetTraversalStrategies.standard_strategies())
            )
        ),
    )

    target_types = typer.Option(
        "@molecular",
        "--targets",
        show_default=False,
        help=doc(
            """
        The accepted target types, comma-separated.

        NOTE: This affects only the types are are accepted after traversal,
        and the types must be included in the traversal.
        This means that this must be AT LEAST as restrictive as the traversal strategy.

        The ChEMBL-defined types are:

          {}

        These special names are also accepted:

          - {}

        [default: @molecular]
        """.format(
                "; ".join([s.name for s in TargetType.all_types()]),
                "\n\n          - ".join(
                    [f"{k} ({v})" for k, v in TargetType.special_type_names().items()]
                ),
            )
        ),
    )

    min_confidence = typer.Option(
        3,
        "--confidence",
        min=0,
        max=9,
        show_default=False,
        help=doc(
            """
        Minimum target confidence score, inclusive.
        This is useful to modify in only some cases. More important options are min_pchembl and taxa.

        Values are: {}

        [default: 3]
        """.format(
                "; ".join([f"{s.value} ({s.name})" for s in ConfidenceLevel])
            )
        ),
    )

    relations = typer.Option(
        "<,<=,=",
        "--relations",
        show_default=False,
        help=doc(
            """
        Assay activity relations allowed, comma-separated.
        If post-processing yourself, consider including all.
        Values are: <, <=, =, >, >=, ~.
        [default: <,<=,=]
        """
        ),
    )

    min_pchembl = typer.Option(
        6.0,
        "--pchembl",
        min=0.0,
        show_default=False,
        help=doc(
            """
        Minimum pCHEMBL value, inclusive.
        If post-processing yourself, consider setting to 0.0.
        [default: 6.0]
        """
        ),
    )

    banned_flags = typer.Option(
        "@negative",
        show_default=False,
        help=doc(
            """
        Exclude activity annotations with data validity flags, comma-separated.
        It is rare to need to change this.

        Values are: {}.

        Special sets are:

          - @all (all flags are banned)

          - @negative ({})

          - @positive ({})

        [default: @negative]
        """.format(
                "; ".join([s.name for s in DataValidityComment]),
                ", ".join([s.name for s in DataValidityComment.negative_comments()]),
                ", ".join([s.name for s in DataValidityComment.positive_comments()]),
            ),
        ),
    )

    binding_search_name = typer.Option(
        None,
        help="""
        The fully qualified name of a class inheriting ``BindingSearch``.
        If specified, all parameters above are passed to its constructor.
        """,
    )

    chembl_trial = typer.Option(
        0,
        "--phase",
        show_default=False,
        help=doc(
            """
        Minimum phase of a clinical trial, inclusive.
        Values are: 0, 1, 2, 3.
        [default: 0]
        """
        ),
        min=0,
        max=3,
    )

    KNOWN_USEFUL_KEYS: Mapping[str, str] = {
        "weight": "Molecular Weight",
        "xlogp3": None,
        "hydrogen-bond-donors": "Hydrogen Bond Donor Count",
        "hydrogen-bond-acceptors": "Hydrogen Bond Acceptor Count",
        "rotatable-bonds": "Rotatable Bond Count",
        "exact-mass": None,
        "monoisotopic-mass": None,
        "tpsa": "Topological Polar Surface Area",
        "heavy-atoms": "Heavy Atom Count",
        "charge": "Formal Charge",
        "complexity": None,
    }
    KNOWN_USELESS_KEYS: Mapping[str, str] = {
        "components": "Covalently-Bonded Unit Count",
        "isotope-atoms": "Isotope Atom Count",
        "defined-atom-stereocenter-count": None,
        "undefined-atom-stereocenter-count": None,
        "defined-bond-stereocenter-count": None,
        "undefined-bond-stereocenter-count": None,
        "compound-is-canonicalized": None,
    }

    pubchem_computed_keys = typer.Option(
        "weight,xlogp3,tpsa,complexity,exact-mass,heavy-atom-count,charge",
        help="""
            The keys of the computed properties, comma-separated.
            Key names are case-insensitive and ignore punctuation like underscores and hyphens.

            Known keys are: {}

            Known, less-useful (metadata-like) keys are: {}
        """.format(
            _stringify(KNOWN_USEFUL_KEYS), _stringify(KNOWN_USELESS_KEYS)
        ),
    )


__all__ = ["EntryArgs"]
