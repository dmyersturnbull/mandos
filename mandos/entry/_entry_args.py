from inspect import cleandoc
from typing import Mapping

import typer

from mandos.entry._arg_utils import Opt, ArgUtils
from mandos.model.apis.chembl_support.chembl_activity import DataValidityComment
from mandos.model.apis.chembl_support.chembl_targets import ConfidenceLevel, TargetType
from mandos.model.apis.chembl_support.target_traversal import TargetTraversalStrategies


def _stringify(keys: Mapping[str, str]):
    return ", ".join((k if v is None else f"{k} ({v.lower()})" for k, v in keys.items()))


class EntryArgs:
    @staticmethod
    def key(name: str) -> typer.Option:
        return typer.Option(
            name,
            min=1,
            max=120,
            help=cleandoc(
                r"""
                A unique key to designate the search.

                Should be a short, <60-character name that describes the search and parameters.
                Intermediate output filenames will use this value.
                """
            ),
        )

    check = Opt.flag(
        r"Do not run searches; just check that the parameters are ok.",
        hidden=True,
    )

    ###############################################################################################
    #                                         CHEMBL                                              #
    ###############################################################################################

    traversal_strategy = typer.Option(
        "@null",
        "--traversal",
        show_default=False,
        help=cleandoc(
            rf"""
            Target traversal strategy name, file, or class.
            Dictates the way the network of ChEMBL targets is traversed (from the annotated target as a source).
            Specifies the network links that are followed and which targets are 'accepted' for final annotations.
            This has a dramatic effect. See the docs.

            Please note that these are experimental options.

            Can be one of:
            (A) A standard strategy name, starting with @;
            (B) The path to a ``*.strat`` file; OR
            (C) The fully qualified name of a ``TargetTraversal``

            The standard traversal strategies are: {ArgUtils.list(TargetTraversalStrategies.standard_strategies())}

            [default: @null] (No traversal; leave targets as-is)
            """
        ),
    )

    target_types = typer.Option(
        "@molecular",
        "--targets",
        help=cleandoc(
            f"""
            The accepted target types, comma-separated.

            NOTE: This affects only the types are are accepted after traversal,
            and the types must be included in the traversal.
            This means that this must be AT LEAST as restrictive as the traversal strategy.

            The ChEMBL-defined types are:
            {ArgUtils.list(TargetType.all_types(), "name")}

            These special names are also accepted:

            {ArgUtils.definition_bullets(TargetType.special_type_names())}
            """
        ),
    )

    min_confidence = typer.Option(
        3,
        "--confidence",
        min=0,
        max=9,
        show_default=False,
        help=cleandoc(
            rf"""
            Minimum target confidence score, inclusive.

            This is useful to modify in only some cases.
            More important options are min_pchembl and taxa.

            Values are: {ArgUtils.list([f"{s.value} ({s.name})" for s in ConfidenceLevel])}

            [default: 3] ("Target assigned is molecular non-protein target")
            """
        ),
    )

    relations = typer.Option(
        "<,<=,=",
        "--relations",
        help=cleandoc(
            """
            Assay activity relations allowed, comma-separated.

            Include all if ``cutoff`` is set.
            Values are: <, <=, =, >, >=, ~.
            """
        ),
    )

    min_pchembl = typer.Option(
        0.0,
        "--min-pchembl",
        min=0.0,
        help=cleandoc(
            """
            Minimum pCHEMBL value, inclusive.

            Set to 0 if ``cutoff`` is set.
            """
        ),
    )

    binds_cutoff = typer.Option(
        7.0,
        "--binding",
        min=0.0,
        show_default=False,
        help=cleandoc(
            """
            Cutoff of pCHEMBL at which "binds" is declared.

            Applies only if the relation is >, >=, =, or ~.

            [default: 7.0 (100 nanomolar)]
            """
        ),
    )

    does_not_bind_cutoff = typer.Option(
        4.0,
        "--nonbinding",
        min=0.0,
        show_default=False,
        help=cleandoc(
            r"""
            Cutoff of pCHEMBL at which "does not bind" is declared.

            Applies only if the relation is <, <=, =, or ~.

            [default: 4.0 (100 micromolar)]
            """
        ),
    )

    min_threshold = typer.Option(
        70,
        "--min-threshold",
        min=70,
        help=cleandoc(
            """
            Minimum pCHEMBL threshold used to limit the true examples when training the QSAR model.

            Must be either 70, 80, or 90.
            An "active" or "inactive" prediction is required for this threshold or higher.
            """
        ),
    )

    banned_flags = typer.Option(
        "@negative",
        help=cleandoc(
            rf"""
            Exclude activity annotations with data validity flags, comma-separated.

            It is rare to need to change this.

            Values are: {ArgUtils.list(DataValidityComment)}.

            Special sets are:

              - @all (all flags are banned)

              - @negative {ArgUtils.list(DataValidityComment.negative_comments())})

              - @positive ({ArgUtils.list(DataValidityComment.positive_comments())})
            """
        ),
    )

    binding_search_name = typer.Option(
        None,
        help=cleandoc(
            r"""
            The fully qualified name of a class inheriting ``BindingSearch``.

            If specified, all parameters above are passed to its constructor.
            """
        ),
    )

    chembl_trial = typer.Option(
        0,
        "--phase",
        help=cleandoc(
            r"""
            Minimum clinical trial phase, inclusive.

            Values are: 0, 1, 2, 3.
            """
        ),
        min=0,
        max=3,
    )

    atc_level = typer.Option("1,2,3,4", help="""List of ATC levels, comma-separated.""")

    ###############################################################################################
    #                                         PUBCHEM                                             #
    ###############################################################################################

    min_cooccurrence_score = typer.Option(
        0.0,
        help=r"Minimum enrichment score, inclusive. See the docs.",
        min=0.0,
    )

    min_cooccurring_articles = typer.Option(
        0,
        help=r"Minimum number of articles for both the compound and object, inclusive.",
        min=0,
    )

    name_must_match = Opt.flag(
        r"""
        Require that the name of the compound(s) exactly matches those on PubChem (case-insensitive).
        """
    )

    banned_sources = Opt.val(
        r"""
        Comma-separated list of sources to exclude.
        """
    )

    min_nanomolar = Opt.val(
        r"""
        Minimum tissue concentration in nanomolar required to include.
        """,
        default=1,
    )

    acute_effect_level = typer.Option(
        2,
        min=1,
        max=2,
        help=cleandoc(
            r"""
            The level in the ChemIDPlus hierarchy of effect names.
            Level 1: e.g. 'behavioral'; level 2: 'behavioral: excitement'
            """
        ),
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
        help=cleandoc(
            rf"""
            The keys of the computed properties, comma-separated.

            Key names are case-insensitive and ignore punctuation like underscores and hyphens.

            Known keys are: {_stringify(KNOWN_USEFUL_KEYS)}

            Known, less-useful (metadata-like) keys are: {_stringify(KNOWN_USELESS_KEYS)}
            """
        ),
    )

    ###############################################################################################
    #                                           G2P                                               #
    ###############################################################################################

    ###############################################################################################
    #                                          HMDB                                               #
    ###############################################################################################

    ###############################################################################################
    #                                          META                                               #
    ###############################################################################################


__all__ = ["EntryArgs"]
