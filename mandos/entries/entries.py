"""
Run searches and write files.
"""

from __future__ import annotations

import abc
import logging
from inspect import cleandoc as doc
from pathlib import Path
from typing import TypeVar, Generic, Union, Mapping, Set, Sequence, Type

import typer

from mandos.model import ReflectionUtils, InjectionError
from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import DataValidityComment
from mandos.model.chembl_support.chembl_targets import TargetType, ConfidenceLevel
from mandos.model.pubchem_support.pubchem_models import ClinicalTrialsGovUtils, CoOccurrenceType
from mandos.model.searches import Search
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy import Taxonomy
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.entries.api_singletons import Apis
from mandos.search.chembl.target_traversal import TargetTraversalStrategies
from mandos.search.pubchem.dgidb_search import DgiSearch, CgiSearch
from mandos.entries.searcher import Searcher

Chembl, Pubchem = Apis.Chembl, Apis.Pubchem
from mandos.search.chembl.binding_search import BindingSearch
from mandos.search.chembl.atc_search import AtcSearch
from mandos.search.chembl.go_search import GoType, GoSearch
from mandos.search.chembl.indication_search import IndicationSearch
from mandos.search.chembl.mechanism_search import MechanismSearch
from mandos.search.pubchem.cooccurrence_search import (
    GeneCoOccurrenceSearch,
    ChemicalCoOccurrenceSearch,
    CoOccurrenceSearch,
)
from mandos.search.pubchem.disease_search import DiseaseSearch

logger = logging.getLogger(__package__)

S = TypeVar("S", bound=Search, covariant=True)


class Utils:
    """"""

    @staticmethod
    def split(st: str) -> Set[str]:
        return {s.strip() for s in st.split(",")}

    @staticmethod
    def get_taxa(taxa: str) -> Sequence[Taxonomy]:
        return [
            TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(int(taxon))
            for taxon in taxa.split(",")
        ]

    @staticmethod
    def get_trial_statuses(st: str) -> Set[str]:
        return ClinicalTrialsGovUtils.resolve_statuses(st)

    @staticmethod
    def get_target_types(st: str) -> Set[str]:
        return {s.name for s in TargetType.resolve(st)}

    @staticmethod
    def get_flags(st: str) -> Set[str]:
        return {s.name for s in DataValidityComment.resolve(st)}


class _Typer:

    path = typer.Argument(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help=doc(
            """
            The path to the input file.
            One of:

              (A) *.txt or *.lines with one InChI Key per line;

              (B) A *.csv, *.tsv, *.tab file (or .gzip variant) with a column called 'inchikey'; OR

              (C) An Apache Arrow *.feather file with a column called 'inchikey'
        """
        ),
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

    taxa = typer.Option(
        "7742",
        show_default=False,
        help=doc(
            """
        The IDs or names of UniProt taxa, comma-separated.
        Taxon names and common names can be used for vertebrate species (where available).

        This can have a significant effect on the search. See the docs fore more info.

        [default: 7742] (Euteleostomi)
        """
        ),
    )

    traversal_strategy = typer.Option(
        "@null",
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

    test = typer.Option(False, help="Do not run searches; just check that the parameters are ok.")

    chembl_trial = typer.Option(
        3,
        show_default=False,
        help=doc(
            """
        Minimum phase of a clinical trial, inclusive.
        Values are: 0, 1, 2, 3.
        [default: 3]
        """
        ),
        min=0,
        max=3,
    )


class Entry(Generic[S], metaclass=abc.ABCMeta):
    @classmethod
    def cmd(cls) -> str:
        key = cls._get_default_key()
        if isinstance(key, typer.models.OptionInfo):
            key = key.default
        if key is None or not isinstance(key, str):
            raise AssertionError(f"Key for {cls.__name__} is {key}")
        return key

    @classmethod
    def run(cls, path: Path, **params) -> None:
        raise NotImplementedError()

    @classmethod
    def get_search_type(cls) -> Type[S]:
        # noinspection PyTypeChecker
        return ReflectionUtils.get_generic_arg(cls, Search)

    @classmethod
    def test(cls, path: Path, **params) -> None:
        params = dict(params)
        params["test"] = True
        cls.run(**params)

    @classmethod
    def _run(cls, built: S, path: Path, test: bool):
        searcher = Searcher([built], path)
        if not test:
            searcher.search()
        return searcher

    # @classmethod
    # def build(cls, path: Path, **params: Mapping[str, Union[int, float, str]]) -> Search:
    #    raise NotImplementedError()

    @classmethod
    def default_param_values(cls) -> Mapping[str, Union[str, float, int]]:
        return {
            param: value
            for param, value in ReflectionUtils.default_arg_values(cls.run).items()
            if param not in {"key", "path"}
        }

    @classmethod
    def _get_default_key(cls) -> str:
        vals = ReflectionUtils.default_arg_values(cls.run)
        try:
            return vals["key"]
        except KeyError:
            logger.error(f"key not in {vals.keys()} for {cls.__name__}")
            raise


class EntryChemblBinding(Entry[BindingSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("chembl:binding"),
        taxa=_Typer.taxa,
        traversal=_Typer.traversal_strategy,
        target_types=_Typer.target_types,
        confidence=_Typer.min_confidence,
        relations=_Typer.relations,
        min_pchembl=_Typer.min_pchembl,
        banned_flags=_Typer.banned_flags,
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch binding data from ChEMBL.
        These are 'activity' annotations of the type 'B' that have a pCHEMBL value.
        There is extended documentation on this search; see:

        https://mandos-chem.readthedocs.io/en/latest/binding.html
        """
        built = BindingSearch(
            key=key,
            api=Chembl,
            taxa=Utils.get_taxa(taxa),
            traversal_strategy=traversal,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=confidence,
            allowed_relations=Utils.split(relations),
            min_pchembl=min_pchembl,
            banned_flags=Utils.get_flags(banned_flags),
        )
        return cls._run(built, path, test)


class EntryChemblMechanism(Entry[MechanismSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("chembl:mechanism"),
        taxa=_Typer.taxa,
        traversal=_Typer.traversal_strategy,
        target_types=_Typer.target_types,
        min_confidence=_Typer.min_confidence,
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch mechanism of action (MoA) data from ChEMBL.
        """
        built = MechanismSearch(
            key=key,
            api=Chembl,
            taxa=Utils.get_taxa(taxa),
            traversal_strategy=traversal,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=min_confidence,
        )
        return cls._run(built, path, test)


class EntryChemblTrials(Entry[IndicationSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("chembl.trials"),
        min_phase=_Typer.chembl_trial,
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch clinical trials recorded in ChEMBL.
        """
        built = IndicationSearch(key=key, api=Chembl, min_phase=min_phase)
        return cls._run(built, path, test)


class EntryChemblAtc(Entry[AtcSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("chembl.atc"),
        levels=typer.Option(
            "1,2,3,4,5", min=1, max=5, help="""List of ATC levels, comma-separated."""
        ),
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch ATC codes from ChEMBL.
        """
        built = AtcSearch(key=key, api=Chembl, levels={int(x.strip()) for x in levels.split(",")})
        return cls._run(built, path, test)


class _EntryChemblGo(Entry[GoSearch], metaclass=abc.ABCMeta):
    @classmethod
    def go_type(cls) -> GoType:
        raise NotImplementedError()

    @classmethod
    def cmd(cls) -> str:
        return f"chembl:go.{cls.go_type().name.lower()}"

    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("<see above>"),
        taxa=_Typer.taxa,
        traversal_strategy=_Typer.traversal_strategy,
        target_types=_Typer.target_types,
        confidence=_Typer.min_confidence,
        relations=_Typer.relations,
        min_pchembl=_Typer.min_pchembl,
        banned_flags=_Typer.banned_flags,
        binding_search=typer.Option(
            None,
            help="""
            The fully qualified name of a class inheriting ``BindingSearch``.
            If specified, all parameters above are passed to its constructor.
            """,
        ),
        test=_Typer.test,
    ) -> Searcher:
        """
        Process data.

        Note:

            By default, the key is the "chembl:go.function", "chembl:go.process", or "chembl:go.component".
        """
        if key is None:
            key = cls.cmd()
        api = ChemblApi.wrap(Chembl)
        if binding_search is None:
            binding_clazz = BindingSearch
        else:
            binding_clazz = ReflectionUtils.injection(binding_search, BindingSearch)
            logger.info(f"NOTICE: Passing parameters to {binding_clazz.__qualname__}")
        try:
            binding_search = binding_clazz(
                key=key,
                api=Chembl,
                taxa=Utils.get_taxa(taxa),
                traversal_strategy=traversal_strategy,
                allowed_target_types=Utils.get_target_types(target_types),
                min_confidence_score=confidence,
                allowed_relations=Utils.split(relations),
                min_pchembl=min_pchembl,
                banned_flags=Utils.get_flags(banned_flags),
            )
        except (TypeError, ValueError):
            raise InjectionError(f"Failed to build {binding_clazz.__qualname__}")
        built = GoSearch(key, api, cls.go_type(), binding_search)
        return cls._run(built, path, test)


class EntryGoFunction(_EntryChemblGo):
    @classmethod
    def go_type(cls) -> GoType:
        return GoType.function


class EntryGoProcess(_EntryChemblGo):
    @classmethod
    def go_type(cls) -> GoType:
        return GoType.process


class EntryGoComponent(_EntryChemblGo):
    @classmethod
    def go_type(cls) -> GoType:
        return GoType.component


class EntryPubchemDisease(Entry[DiseaseSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("disease.ctd:mesh"),
        therapeutic=typer.Option(True, help="Include annotations of type 'therapeutic'"),
        marker=typer.Option(True, help="Include annotations of type 'marker/mechanism'"),
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch MeSH codes of diseases and disorders in the Comparative Toxicogenomics Database (CTD).
        """
        built = DiseaseSearch(key, Pubchem, therapeutic=therapeutic, marker=marker)
        return cls._run(built, path, test)


class EntryPubchemDgi(Entry[DgiSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("disease.dgidb:dgis"),
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch DRUG/gene interactions in the Drug Gene Interaction Database (DGIDB).
        Also see ``disease.dgidb:cgis``.
        """
        built = DgiSearch(key, Pubchem)
        return cls._run(built, path, test)


class EntryPubchemCgi(Entry[CgiSearch]):
    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("disease.dgidb:cgis"),
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch COMPOUND/gene interactions in the Drug Gene Interaction Database (DGIDB).
        Also see ``disease.dgidb:dgis``.
        """
        built = CgiSearch(key, Pubchem)
        return cls._run(built, path, test)


U = TypeVar("U", covariant=True, bound=CoOccurrenceSearch)


class _EntryPubchemCoOccurrence(Entry[U], metaclass=abc.ABCMeta):
    @classmethod
    def cmd(cls) -> str:
        return f"lit.pubchem:{cls.get_cooccurrence_type().name.lower()}"

    @classmethod
    def get_cooccurrence_type(cls) -> CoOccurrenceType:
        s: CoOccurrenceSearch = cls.get_search_type()
        return s.cooccurrence_type()

    @classmethod
    def run(
        cls,
        path=_Typer.path,
        key=_Typer.key("<see above>"),
        min_score=typer.Option(
            0.0,
            help="Minimum enrichment score, inclusive. See docs for more info.",
            min=0.0,
        ),
        min_articles=typer.Option(
            0,
            help="Minimum number of articles for both the compound and object, inclusive.",
            min=0,
        ),
        test=_Typer.test,
    ) -> Searcher:
        """
        Fetch co-occurrences from PubMed articles.
        There is extended documentation on this search.
        Also refer to https://pubchemdocs.ncbi.nlm.nih.gov/knowledge-panels
        """
        if key is None:
            key = cls.cmd()
        clazz = cls.get_search_type()
        built = clazz(key, Pubchem, min_score=min_score, min_articles=min_articles)
        return cls._run(built, path, test)


class EntryPubchemGeneCoOccurrence(_EntryPubchemCoOccurrence[GeneCoOccurrenceSearch]):
    """"""


class EntryPubchemDiseaseCoOccurrence(_EntryPubchemCoOccurrence[GeneCoOccurrenceSearch]):
    """"""


class EntryPubchemChemicalCoOccurrence(_EntryPubchemCoOccurrence[ChemicalCoOccurrenceSearch]):
    """"""


Entries = [
    EntryChemblBinding,
    EntryChemblMechanism,
    EntryChemblAtc,
    EntryChemblTrials,
    EntryGoFunction,
    EntryGoProcess,
    EntryGoComponent,
    EntryPubchemDisease,
    EntryPubchemGeneCoOccurrence,
    EntryPubchemDiseaseCoOccurrence,
    EntryPubchemChemicalCoOccurrence,
]
