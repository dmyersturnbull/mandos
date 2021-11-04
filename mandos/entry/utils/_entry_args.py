from inspect import cleandoc
from typing import Mapping

import decorateme
import typer

from mandos.entry.utils._arg_utils import ArgUtils, Opt
from mandos.model.apis.chembl_support.chembl_targets import ConfidenceLevel, TargetType
from mandos.model.apis.chembl_support.target_traversal import TargetTraversalStrategies


def _stringify(keys: Mapping[str, str]):
    return ", ".join((k if v is None else f"{k} ({v.lower()})" for k, v in keys.items()))


@decorateme.auto_utils()
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

                A <60-character name that describes the search and parameters.
                Intermediate output filenames will use this value.
                """
            ),
        )

    check = Opt.flag(
        r"Do not run searches; just check everything.",
        hidden=True,
    )

    ###############################################################################################
    #                                         CHEMBL                                              #
    ###############################################################################################

    traversal = typer.Option(
        "@null",
        "--traversal",
        show_default=False,
        help=cleandoc(
            rf"""
            Target traversal strategy name, file, or class.
            This is an experimental option. See the docs.

            Can be one of:
            (A) A standard strategy name, starting with @;
            (B) The path to a *.strat file; OR
            (C) The fully qualified name of a TargetTraversal

            Standard strategies:
            {ArgUtils.list(TargetTraversalStrategies.standard_strategies(), sep="; ")}

            [default: @null] (leave targets as-is)
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
            {ArgUtils.list(TargetType)}

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

            Values are: {ArgUtils.list(ConfidenceLevel)}

            [default: 3] ("Target assigned is molecular non-protein target")
            """
        ),
    )

    min_pchembl = typer.Option(
        0.0,
        "--pchembl",
        min=0.0,
        help=cleandoc(
            """
            Minimum pCHEMBL value, inclusive.

            Set to 0 if "cutoff" is set.
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

    pubchem_trial_phase = typer.Option(
        0,
        "--phase",
        help=cleandoc(
            r"""
            Minimum clinical trial pseudo-phase.

            Values are: 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0
            """
        ),
        min=0,
        max=4,
    )

    pubchem_trial_statuses = Opt.val(
        r"""
        Trial pseudo-statuses, comma-separated.

        Values are: "unknown", "completed", "stopped", and "ongoing".
        """,
    )

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

    match_name = Opt.flag(
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
            (E.g. 'behavioral' for level 1 and 'behavioral: excitement' for level 2.)
            """
        ),
    )

    req_explicit = Opt.flag(
        r"""
        Require the compound to be listed explicitly as an intervention.
        """
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

            Keys are case-insensitive and mainly ignore punctuation.

            Main keys: {_stringify(KNOWN_USEFUL_KEYS)}

            Less-useful keys: {_stringify(KNOWN_USELESS_KEYS)}
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

    random_n = typer.Option(
        1000,
        help=cleandoc(
            rf"""
            The number of classes to choose from (max n for int).
            """
        ),
    )


__all__ = ["EntryArgs"]
