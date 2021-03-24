"""
Run searches and write files.
"""

from __future__ import annotations

import abc
from inspect import cleandoc as doc
from pathlib import Path
from typing import TypeVar, Generic, Union, Mapping, Set, Sequence, Type, Optional

import typer

from mandos.model import ReflectionUtils, InjectionError
from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import DataValidityComment
from mandos.model.chembl_support.chembl_targets import TargetType, ConfidenceLevel
from mandos.model.pubchem_support.pubchem_models import (
    ClinicalTrialsGovUtils,
    CoOccurrenceType,
    AssayType,
)
from mandos.model.searches import Search
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy import Taxonomy
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.entries.api_singletons import Apis
from mandos.search.chembl.target_traversal import TargetTraversalStrategies
from mandos.search.pubchem.bioactivity_search import BioactivitySearch
from mandos.search.pubchem.dgidb_search import DgiSearch
from mandos.search.pubchem.ctd_gene_search import CtdGeneSearch
from mandos.entries.searcher import Searcher
from mandos.search.pubchem.drugbank_ddi_search import DrugbankDdiSearch
from mandos.search.pubchem.drugbank_interaction_search import (
    DrugbankTargetSearch,
    DrugbankGeneralFunctionSearch,
)

from mandos import logger
from mandos.search.chembl.binding_search import BindingSearch
from mandos.search.chembl.atc_search import AtcSearch
from mandos.search.chembl.go_search import GoType, GoSearch
from mandos.search.chembl.indication_search import IndicationSearch
from mandos.search.chembl.mechanism_search import MechanismSearch
from mandos.search.pubchem.cooccurrence_search import (
    GeneCoOccurrenceSearch,
    ChemicalCoOccurrenceSearch,
    CoOccurrenceSearch,
    DiseaseCoOccurrenceSearch,
)
from mandos.search.pubchem.disease_search import DiseaseSearch

S = TypeVar("S", bound=Search, covariant=True)
U = TypeVar("U", covariant=True, bound=CoOccurrenceSearch)


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
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
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

    to = typer.Option(
        None,
        show_default=False,
        help=doc(
            """
            The path to the output file.
            If not set, chooses <input-path>-<search>.csv.gz
            The filename extension should be one of: .csv, .tsv, .tab, .json (with optional .gz/.bz2);
            .feather; .snappy (or .parquet); or .h5.
            Feather (.feather), Parquet (.snappy), and tab-delimited (.tsv.gz) are recommended.
            JSON and HDF5 (.h5) are not recommended. If H5, will add a new dataset named <key> to the archive.
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

    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Configure logger to output INFO (use `--verbose --verbose` or `-vv` for DEBUG output)",
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

        This can have a significant effect on the search. See the docs fore more info.

        [default: 7742] (Euteleostomi)
        """
        ),
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

    chembl_trial = typer.Option(
        3,
        "--phase",
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
    def _run(cls, built: S, path: Path, to: Optional[Path], check: bool):
        searcher = Searcher([built], path)
        if not check:
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
        path: Path = _Typer.path,
        key: str = _Typer.key("chembl:binding"),
        to: Optional[Path] = _Typer.to,
        taxa: Optional[str] = _Typer.taxa,
        traversal=_Typer.traversal_strategy,
        target_types=_Typer.target_types,
        confidence=_Typer.min_confidence,
        relations=_Typer.relations,
        min_pchembl=_Typer.min_pchembl,
        banned_flags=_Typer.banned_flags,
        check: bool = _Typer.test,
    ) -> Searcher:
        """
        Binding data from ChEMBL.
        These are 'activity' annotations of the type 'B' that have a pCHEMBL value.
        There is extended documentation on this search; see:

        https://mandos-chem.readthedocs.io/en/latest/binding.html

        OBJECT: ChEMBL preferred target name

        PREDICATE: "binds"
        """
        built = BindingSearch(
            key=key,
            api=Apis.Chembl,
            taxa=Utils.get_taxa(taxa),
            traversal_strategy=traversal,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=confidence,
            allowed_relations=Utils.split(relations),
            min_pchembl=min_pchembl,
            banned_flags=Utils.get_flags(banned_flags),
        )
        return cls._run(built, path, to, check)


class EntryChemblMechanism(Entry[MechanismSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("chembl:mechanism"),
        to: Optional[Path] = _Typer.to,
        taxa: Optional[str] = _Typer.taxa,
        traversal: str = _Typer.traversal_strategy,
        target_types: str = _Typer.target_types,
        min_confidence: Optional[int] = _Typer.min_confidence,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Mechanism of action (MoA) data from ChEMBL.

        OBJECT: ChEMBL preferred target name

        PREDICATE: Target action; e.g. "agonist" or "positive allosteric modulator"
        """
        built = MechanismSearch(
            key=key,
            api=Apis.Chembl,
            taxa=Utils.get_taxa(taxa),
            traversal_strategy=traversal,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=min_confidence,
        )
        return cls._run(built, path, to, check)


class EntryChemblTrials(Entry[IndicationSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("chembl.trial"),
        to: Optional[Path] = _Typer.to,
        min_phase: Optional[int] = _Typer.chembl_trial,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Diseases from clinical trials listed in ChEMBL.

        OBJECT: MeSH code

        PREDICATE: "phase <level> trial"
        """
        built = IndicationSearch(key=key, api=Apis.Chembl, min_phase=min_phase)
        return cls._run(built, path, to, check)


class EntryChemblAtc(Entry[AtcSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("chembl.atc"),
        to: Optional[Path] = _Typer.to,
        levels: str = typer.Option(
            "1,2,3,4,5", min=1, max=5, help="""List of ATC levels, comma-separated."""
        ),
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        ATC codes from ChEMBL.

        OBJECT: ATC Code

        PREDICATE: "ATC L<leveL> code"
        """
        built = AtcSearch(
            key=key, api=Apis.Chembl, levels={int(x.strip()) for x in levels.split(",")}
        )
        return cls._run(built, path, to, check)


class _EntryChemblGo(Entry[GoSearch], metaclass=abc.ABCMeta):
    @classmethod
    def go_type(cls) -> GoType:
        raise NotImplementedError()

    @classmethod
    def cmd(cls) -> str:
        me = str(cls.go_type().name)
        return f"chembl:go.{me.lower()}"

    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("<see above>"),
        to: Optional[Path] = _Typer.to,
        taxa: Optional[str] = _Typer.taxa,
        traversal_strategy: str = _Typer.traversal_strategy,
        target_types: str = _Typer.target_types,
        confidence: Optional[int] = _Typer.min_confidence,
        relations: str = _Typer.relations,
        min_pchembl: float = _Typer.min_pchembl,
        banned_flags: Optional[str] = _Typer.banned_flags,
        binding_search: Optional[str] = typer.Option(
            None,
            help="""
            The fully qualified name of a class inheriting ``BindingSearch``.
            If specified, all parameters above are passed to its constructor.
            """,
        ),
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        GO terms associated with ChEMBL binding targets.

        OBJECT: GO Term name

        PREDICATE: "GO ""Function"|"Process"|"Component"" term"

        Note:

            By default, the key is the "chembl:go.function", "chembl:go.process", or "chembl:go.component".
        """
        if key is None or key == "<see above>":
            key = cls.cmd()
        api = ChemblApi.wrap(Apis.Chembl)
        if binding_search is None:
            binding_clazz = BindingSearch
        else:
            binding_clazz = ReflectionUtils.injection(binding_search, BindingSearch)
            logger.info(f"NOTICE: Passing parameters to {binding_clazz.__qualname__}")
        try:
            binding_search = binding_clazz(
                key=key,
                api=Apis.Chembl,
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
        return cls._run(built, path, to, check)


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
        path: Path = _Typer.path,
        key: str = _Typer.key("disease.ctd:mesh"),
        to: Optional[Path] = _Typer.to,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Diseases in the Comparative Toxicogenomics Database (CTD).

        OBJECT: MeSH code of disease

        PREDICATE: "marker/mechanism" or "disease"
        """
        built = DiseaseSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check)


class _EntryPubchemCoOccurrence(Entry[U], metaclass=abc.ABCMeta):
    @classmethod
    def cmd(cls) -> str:
        me = str(cls.get_cooccurrence_type().name)
        return f"lit.pubchem:{me.lower()}"

    @classmethod
    def get_cooccurrence_type(cls) -> CoOccurrenceType:
        s: CoOccurrenceSearch = cls.get_search_type()
        return s.cooccurrence_type()

    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("<see above>"),
        to: Optional[Path] = _Typer.to,
        min_score: float = typer.Option(
            0.0,
            help="Minimum enrichment score, inclusive. See docs for more info.",
            min=0.0,
        ),
        min_articles: int = typer.Option(
            0,
            help="Minimum number of articles for both the compound and object, inclusive.",
            min=0,
        ),
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Co-occurrences from PubMed articles.
        There is extended documentation on this search.
        Also refer to https://pubchemdocs.ncbi.nlm.nih.gov/knowledge-panels

        OBJECT: Name of gene/chemical/disease

        PREDICATE: "<gene/chemical/disease> co-occurrence"
        """
        if key is None or key == "<see above>":
            key = cls.cmd()
        clazz = cls.get_search_type()
        built = clazz(key, Apis.Pubchem, min_score=min_score, min_articles=min_articles)
        return cls._run(built, path, to, check)


class EntryPubchemGeneCoOccurrence(_EntryPubchemCoOccurrence[GeneCoOccurrenceSearch]):
    """"""


class EntryPubchemDiseaseCoOccurrence(_EntryPubchemCoOccurrence[DiseaseCoOccurrenceSearch]):
    """"""


class EntryPubchemChemicalCoOccurrence(_EntryPubchemCoOccurrence[ChemicalCoOccurrenceSearch]):
    """"""


class EntryPubchemDgi(Entry[DgiSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("interact.dgidb:gene"),
        to: Optional[Path] = _Typer.to,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Drug/gene interactions in the Drug Gene Interaction Database (DGIDB).
        Also see ``disease.dgidb:int``.

        OBJECT: Name of the gene

        PREDICATE: "drug/gene interaction"
        """
        built = DgiSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check)


class EntryPubchemCgi(Entry[CtdGeneSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("interact.ctd:gene"),
        to: Optional[Path] = _Typer.to,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Compound/gene interactions in the Drug Gene Interaction Database (DGIDB).
        Also see ``interact.dgidb:int``.

        OBJECT: Name of the gene

        PREDICATE: "compound/gene interaction"

        """
        built = CtdGeneSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check)


class EntryDrugbankTarget(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("interact.drugbank:target"),
        to: Optional[Path] = _Typer.to,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Protein targets from DrugBank.

        OBJECT: Target name (e.g. "Solute carrier family 22 member 11") from DrugBank

        PREDICATE: Action (e.g. "binder", "downregulator", or "agonist")
        """
        built = DrugbankTargetSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check)


class EntryGeneralFunction(Entry[DrugbankGeneralFunctionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("interact.drugbank:function"),
        to: Optional[Path] = _Typer.to,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        General functions from DrugBank targets.

        OBJECT: Name of the general function (e.g. "Toxic substance binding")

        PREDICATE: against on target (e.g. "binder", "downregulator", or "agonist").
        """
        built = DrugbankGeneralFunctionSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check)


class EntryDrugbankDdi(Entry[DrugbankDdiSearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("interact.drugbank:ddi"),
        to: Optional[Path] = _Typer.to,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        Drug/drug interactions listed by DrugBank.

        The 'description' column includes useful information about the interaction,
        such as diseases and whether a risk is increased or decreased.

        OBJECT: name of the drug (e.g. "ibuprofen")

        PREDICATE: "ddi"
        """
        built = DrugbankDdiSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check)


class EntryPubchemAssay(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = _Typer.path,
        key: str = _Typer.key("assay.pubchem:activity"),
        to: Optional[Path] = _Typer.to,
        name_must_match: bool = typer.Option(
            False,
            help=doc(
                """
            Require that the name of the compound(s) exactly matches the compound name on PubChem (case-insensitive)
        """
            ),
        ),
        ban_sources: Optional[str] = None,
        check: bool = _Typer.test,
        verbose: int = _Typer.verbose,
    ) -> Searcher:
        """
        PubChem bioactivity results.

        Note: The species name, if present, is taken from the target name.
        The taxon ID is what was curated in PubChem.

        OBJECT: Name of the target without species suffix (e.g. "Slc6a3 - solute carrier family 6 member 3")

        PREDICATE: "active"|"inactive"|"inconclusive"|"undetermined"

        SOURCE: "PubChem: <referrer> "(""confirmatory"|"literature"|"other"")"
        """
        built = BioactivitySearch(
            key, Apis.Pubchem, assay_types=set(AssayType), compound_name_must_match=name_must_match
        )
        return cls._run(built, path, to, check)


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
    EntryPubchemDgi,
    EntryPubchemCgi,
    EntryDrugbankTarget,
    EntryGeneralFunction,
    EntryDrugbankDdi,
    EntryPubchemAssay,
]
