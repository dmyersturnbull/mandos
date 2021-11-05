from typing import Mapping

import decorateme
import typer

from mandos.entry.utils._arg_utils import ArgUtils, Opt
from mandos.model.apis.chembl_support.chembl_targets import ConfidenceLevel, TargetType
from mandos.model.apis.chembl_support.target_traversal import TargetTraversalStrategies
from mandos.model.apis.pubchem_support.pubchem_models import (
    ClinicalTrialPhase,
    ClinicalTrialSimplifiedStatus,
)


def _stringify(keys: Mapping[str, str]):
    return ", ".join((k if v is None else f"{k} ({v.lower()})" for k, v in keys.items()))


@decorateme.auto_utils()
class EntryArgs:
    @staticmethod
    def key(name: str) -> typer.Option:
        return Opt.val(
            r"""
            A unique key to designate the search.

            A <60-character name that describes the search and parameters.
            Intermediate output filenames will use this value.
            """,
            name,
            min=1,
            max=120,
        )

    check = Opt.flag(
        r"Do not run searches; just check everything.",
        hidden=True,
    )

    ###############################################################################################
    #                                         CHEMBL                                              #
    ###############################################################################################

    traversal = Opt.val(
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
        """,
        default="@null",
        show_default=False,
    )

    target_types = Opt.val(
        f"""
        The accepted target types, comma-separated.

        NOTE: This affects only the types are are accepted after traversal,
        and the types must be included in the traversal.
        This means that this must be AT LEAST as restrictive as the traversal strategy.

        The ChEMBL-defined types are:
        {ArgUtils.list(TargetType)}

        These special names are also accepted:

        {ArgUtils.definition_bullets(TargetType.special_type_names())}
        """,
        default="@molecular",
    )

    min_confidence = Opt.val(
        rf"""
        Minimum target confidence score, inclusive.

        This is useful to modify in only some cases.
        More important options are min_pchembl and taxa.

        Values are: {ArgUtils.list(ConfidenceLevel)}

        [default: 3] ("Target assigned is molecular non-protein target")
        """,
        default=3,
        min=0,
        max=9,
        show_default=False,
    )

    min_pchembl = Opt.val(
        r"""
        Minimum pCHEMBL value, inclusive.

        Set to 0 if "cutoff" is set.
        """,
        default=0,
        min=0,
    )

    binds_cutoff = Opt.val(
        r"""
        Cutoff of pCHEMBL at which "binds" is declared.

        Applies only if the relation is >, >=, =, or ~.

        [default: 7.0 (100 nanomolar)]
        """,
        default=7.0,
        min=0.0,
        show_default=False,
    )

    min_threshold = Opt.val(
        r"""
        Minimum pCHEMBL threshold used to limit the true examples when training the QSAR model.

        Must be either 70, 80, or 90.
        An "active" or "inactive" prediction is required for this threshold or higher.
        """,
        default=70,
        min=70,
        max=90,
    )

    binding_search_name = Opt.val(
        r"""
        The fully qualified name of a class inheriting ``BindingSearch``.

        If specified, all parameters above are passed to its constructor.
        """
    )

    chembl_trial = Opt.val(
        r"""
        Minimum clinical trial phase, inclusive.

        Values are: 0, 1, 2, 3, 4.
        """,
        default=0,
        min=0,
        max=4,
    )

    atc_level = Opt.val(r"""List of ATC levels, comma-separated.""", default="1,2,3,4")

    ###############################################################################################
    #                                         PUBCHEM                                             #
    ###############################################################################################

    pubchem_trial_phase = Opt.val(
        rf"""
        Minimum clinical trial pseudo-phase.

        Values are: {", ".join(str(e.score) for e in ClinicalTrialPhase)}.
        """,
        default=0,
        min=0,
        max=max((e.score for e in ClinicalTrialPhase)),
    )

    pubchem_trial_statuses = Opt.val(
        rf"""
        Trial pseudo-statuses, comma-separated.

        Values are: {", ".join(s.name for s in ClinicalTrialSimplifiedStatus)}.
        """,
        default="@all",
    )

    min_cooccurrence_score = Opt.val(
        r"Minimum enrichment score, inclusive. See the docs.",
        default=0.0,
        min=0.0,
    )

    min_cooccurring_articles = Opt.val(
        r"Minimum number of articles for both the compound and object, inclusive.",
        default=0,
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

    acute_effect_level = Opt.val(
        r"""
        The level in the ChemIDPlus hierarchy of effect names.
        (E.g. 'behavioral' for level 1 and 'behavioral: excitement' for level 2.)
        """,
        default=2,
        min=1,
        max=2,
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

    ALL_NON_EMPTY_KEYS = {
        k: v for k, v in {**KNOWN_USEFUL_KEYS, **KNOWN_USELESS_KEYS}.items() if v is not None
    }

    pubchem_computed_keys = Opt.val(
        rf"""
        The keys of the computed properties, comma-separated.

        Keys are case-insensitive and mainly ignore punctuation.

        Main keys: {_stringify(KNOWN_USEFUL_KEYS)}

        Less-useful keys: {_stringify(KNOWN_USELESS_KEYS)}
        """,
        default="weight,xlogp3,tpsa,complexity,exact-mass,heavy-atom-count,charge",
    )

    ###############################################################################################
    #                                           G2P                                               #
    ###############################################################################################

    ###############################################################################################
    #                                          HMDB                                               #
    ###############################################################################################

    min_nanomolar = Opt.val(
        r"""
        Minimum tissue concentration in nanomolar required to include.
        """,
        default=1,
    )

    ###############################################################################################
    #                                          META                                               #
    ###############################################################################################

    random_n = Opt.val(
        rf"""
        The number of classes to choose from (max n for int).
        """,
        default=1000,
    )


__all__ = ["EntryArgs"]
