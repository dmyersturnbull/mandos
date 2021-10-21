"""
Run searches and write files.
"""

from __future__ import annotations

import abc
import inspect
from pathlib import Path
from typing import Optional, TypeVar

from pocketutils.core.exceptions import InjectionError
from pocketutils.tools.reflection_tools import ReflectionTools

from mandos import logger
from mandos.entry.abstract_entries import Entry
from mandos.entry.api_singletons import Apis
from mandos.entry.tools.searchers import Searcher
from mandos.entry.utils._arg_utils import ArgUtils
from mandos.entry.utils._common_args import CommonArgs
from mandos.entry.utils._entry_args import EntryArgs
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.pubchem_support.pubchem_models import (
    CoOccurrenceType,
    DrugbankTargetType,
)
from mandos.model.concrete_hits import GoType
from mandos.search.chembl.atc_search import AtcSearch
from mandos.search.chembl.binding_search import BindingSearch
from mandos.search.chembl.go_search import GoSearch
from mandos.search.chembl.indication_search import IndicationSearch
from mandos.search.chembl.mechanism_search import MechanismSearch
from mandos.search.chembl.target_prediction_search import TargetPredictionSearch
from mandos.search.g2p.g2p_interaction_search import G2pInteractionSearch
from mandos.search.pubchem.acute_effects_search import AcuteEffectSearch, Ld50Search
from mandos.search.pubchem.bioactivity_search import BioactivitySearch
from mandos.search.pubchem.computed_property_search import ComputedPropertySearch
from mandos.search.pubchem.cooccurrence_search import (
    ChemicalCoOccurrenceSearch,
    CoOccurrenceSearch,
    DiseaseCoOccurrenceSearch,
    GeneCoOccurrenceSearch,
)
from mandos.search.pubchem.ctd_gene_search import CtdGeneSearch
from mandos.search.pubchem.dgidb_search import DgiSearch
from mandos.search.pubchem.disease_search import DiseaseSearch
from mandos.search.pubchem.drugbank_ddi_search import DrugbankDdiSearch
from mandos.search.pubchem.drugbank_interaction_search import (
    DrugbankGeneralFunctionSearch,
    DrugbankTargetSearch,
)

U = TypeVar("U", covariant=True, bound=CoOccurrenceSearch)


class EntryChemblBinding(Entry[BindingSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:binding"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        confidence: int = EntryArgs.min_confidence,
        binding: float = EntryArgs.binds_cutoff,
        pchembl: float = EntryArgs.min_pchembl,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Binding data from ChEMBL.

        These are 'activity' annotations of the type 'B' that have a pCHEMBL value.
        https://mandos-chem.readthedocs.io/en/latest/binding.html

        OBJECT: The target name

        WEIGHT: The PCHEMBL value
        """
        tax = ArgUtils.get_taxonomy(taxa)
        built = BindingSearch(
            key=key,
            api=Apis.Chembl,
            taxa=tax,
            traversal=traversal,
            target_types=ArgUtils.get_target_types(target_types),
            min_conf_score=confidence,
            relations={"<", "<=", "="},  # there are no others with pchembl
            min_pchembl=pchembl,
            binds_cutoff=binding,
        )
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryChemblMechanism(Entry[MechanismSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:mechanism"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        min_confidence: Optional[int] = EntryArgs.min_confidence,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Mechanism of action (MOA) data from ChEMBL.

        OBJECT: The target name

        PREDICATE: The target action (e.g. "agonist")
        """
        tax = ArgUtils.get_taxonomy(taxa)
        built = MechanismSearch(
            key=key,
            api=Apis.Chembl,
            taxa=tax,
            traversal=traversal,
            allowed_target_types=ArgUtils.get_target_types(target_types),
            min_confidence_score=min_confidence,
        )
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class ChemblQsarPredictions(Entry[TargetPredictionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:predictions"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        min_threshold: float = EntryArgs.min_threshold,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Predicted target binding from ChEMBL.

        https://mandos-chem.readthedocs.io/en/latest/binding.html
        These are from a QSAR model by ChEMBL.

        OBJECT: The target name

        WEIGHT: The square root of the PCHEMBL threshold
                multiplied by a prediction odds-ratio, normalized
        """
        tax = ArgUtils.get_taxonomy(taxa)
        built = TargetPredictionSearch(
            key=key,
            api=Apis.Chembl,
            scrape=Apis.ChemblScrape,
            taxa=tax,
            traversal=traversal,
            target_types=ArgUtils.get_target_types(target_types),
            min_threshold=min_threshold,
        )
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryChemblTrials(Entry[IndicationSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:trial"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_phase: Optional[int] = EntryArgs.chembl_trial,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Diseases from clinical trials listed in ChEMBL.

        OBJECT: The name of the disease (in MeSH)
        """
        built = IndicationSearch(key=key, api=Apis.Chembl, min_phase=min_phase)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryChemblAtc(Entry[AtcSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:atc"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        levels: str = EntryArgs.atc_level,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        ATC codes from ChEMBL.

        OBJECT: The ATC code name
        """
        built = AtcSearch(
            key=key, api=Apis.Chembl, levels={int(x.strip()) for x in levels.split(",")}
        )
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


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
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("<see above>"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        confidence: Optional[int] = EntryArgs.min_confidence,
        pchembl: float = EntryArgs.min_pchembl,
        binding_search: Optional[str] = EntryArgs.binding_search_name,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        See the docs for the specific entries.
        """
        if key is None or key == "<see above>":
            key = cls.cmd()
        api = ChemblApi.wrap(Apis.Chembl)
        if binding_search is None:
            binding_clazz = BindingSearch
        else:
            binding_clazz = ReflectionTools.injection(binding_search, BindingSearch)
            logger.info(f"Passing parameters to {binding_clazz.__qualname__}")
        try:
            tax = ArgUtils.get_taxonomy(taxa)
            binding_search = binding_clazz(
                key=key,
                api=Apis.Chembl,
                taxa=tax,
                traversal=traversal,
                target_types=ArgUtils.get_target_types(target_types),
                min_conf_score=confidence,
                relations={"<", "<=", "="},
                min_pchembl=pchembl,
            )
        except (TypeError, ValueError):
            raise InjectionError(f"Failed to build {binding_clazz.__qualname__}")
        built = GoSearch(key, api, cls.go_type(), binding_search)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryGoFunction(_EntryChemblGo):
    @classmethod
    def go_type(cls) -> GoType:
        return GoType.function

    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:go.function"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        confidence: Optional[int] = EntryArgs.min_confidence,
        pchembl: float = EntryArgs.min_pchembl,
        binding_search: Optional[str] = EntryArgs.binding_search_name,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        GO Function terms associated with ChEMBL binding targets.

        OBJECT: The GO Function term name

        WEIGHT: The sum of the PCHEMBL values
        """
        args, _, _, locs = inspect.getargvalues(inspect.currentframe())
        return super().run(**{a: locs[a] for a in args if a != "cls"})


class EntryGoProcess(_EntryChemblGo):
    @classmethod
    def go_type(cls) -> GoType:
        return GoType.process

    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:go.process"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        confidence: Optional[int] = EntryArgs.min_confidence,
        pchembl: float = EntryArgs.min_pchembl,
        binding_search: Optional[str] = EntryArgs.binding_search_name,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        GO Process terms associated with ChEMBL binding targets.

        OBJECT: The GO Process term name

        WEIGHT: The sum of the PCHEMBL values
        """
        args, _, _, locs = inspect.getargvalues(inspect.currentframe())
        return super().run(**{a: locs[a] for a in args if a != "cls"})


class EntryGoComponent(_EntryChemblGo):
    @classmethod
    def go_type(cls) -> GoType:
        return GoType.component

    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chembl:go.component"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal,
        target_types: str = EntryArgs.target_types,
        confidence: Optional[int] = EntryArgs.min_confidence,
        pchembl: float = EntryArgs.min_pchembl,
        binding_search: Optional[str] = EntryArgs.binding_search_name,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        GO Component terms associated with ChEMBL binding targets.

        OBJECT: The GO Component term name

        WEIGHT: The sum of the PCHEMBL values
        """
        args, _, _, locs = inspect.getargvalues(inspect.currentframe())
        return super().run(**{a: locs[a] for a in args if a != "cls"})


class EntryPubchemDisease(Entry[DiseaseSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("disease.ctd:mesh"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Diseases in the CTD.

        (Comparative Toxicogenomics Database.)

        OBJECT: The MeSH code of the disease

        """
        built = DiseaseSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


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
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("<see above>"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_score: float = EntryArgs.min_cooccurrence_score,
        min_articles: int = EntryArgs.min_cooccurring_articles,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """See the docstrings for the individual entries."""
        clazz = cls.get_search_type()
        built = clazz(key, Apis.Pubchem, min_score=min_score, min_articles=min_articles)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryPubchemGeneCoOccurrence(_EntryPubchemCoOccurrence[GeneCoOccurrenceSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key(f"lit.pubchem:{CoOccurrenceType.gene.name.lower()}"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_score: float = EntryArgs.min_cooccurrence_score,
        min_articles: int = EntryArgs.min_cooccurring_articles,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Co-occurrences of genes from PubMed articles.

        https://mandos-chem.readthedocs.io/en/latest/co-occurrences.html

        OBJECT: The name of the gene

        WEIGHT: The co-occurrence score (refer to the docs)
        """
        args, _, _, locs = inspect.getargvalues(inspect.currentframe())
        return super().run(**{a: locs[a] for a in args if a != "cls"})


class EntryPubchemDiseaseCoOccurrence(_EntryPubchemCoOccurrence[DiseaseCoOccurrenceSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key(f"lit.pubchem:{CoOccurrenceType.disease.name.lower()}"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_score: float = EntryArgs.min_cooccurrence_score,
        min_articles: int = EntryArgs.min_cooccurring_articles,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Co-occurrences of diseases from PubMed articles.

        https://mandos-chem.readthedocs.io/en/latest/co-occurrences.html

        OBJECT: The name of the disease

        WEIGHT: The co-occurrence score (refer to the docs)
        """
        args, _, _, locs = inspect.getargvalues(inspect.currentframe())
        return super().run(**{a: locs[a] for a in args if a != "cls"})


class EntryPubchemChemicalCoOccurrence(_EntryPubchemCoOccurrence[ChemicalCoOccurrenceSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key(f"lit.pubchem:{CoOccurrenceType.chemical.name.lower()}"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_score: float = EntryArgs.min_cooccurrence_score,
        min_articles: int = EntryArgs.min_cooccurring_articles,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Co-occurrences of chemicals from PubMed articles.

        https://mandos-chem.readthedocs.io/en/latest/co-occurrences.html

        OBJECT: The name of the chemical (e.g. "cocaine")

        WEIGHT: The co-occurrence score (refer to the docs)
        """
        args, _, _, locs = inspect.getargvalues(inspect.currentframe())
        return super().run(**{a: locs[a] for a in args if a != "cls"})


class EntryPubchemDgi(Entry[DgiSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.dgidb:gene"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Drug/gene interactions in the DGIDB.

        Drug Gene Interaction Database.
        Also see disease.dgidb:int.

        OBJECT: The name of the gene

        PREDICATE: "interaction:generic" or "interaction:<type>"
        """
        built = DgiSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryPubchemCgi(Entry[CtdGeneSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.ctd:gene"),
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        to: Optional[Path] = CommonArgs.out_annotations_file,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Compound/gene interactions in the DGIDB.

        Drug Gene Interaction Database.
        Also see ``interact.dgidb:int``.

        OBJECT: The name of the gene

        PREDICATE: derived from the interaction type (e.g. "downregulation")
        """
        built = CtdGeneSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryDrugbankTarget(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.drugbank:targ"),
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        to: Optional[Path] = CommonArgs.out_annotations_file,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Protein targets from DrugBank.

        OBJECT: The target name (e.g. "Solute carrier family 22 member 11")

        PREDICATE: "<target_type>:<action>"
        """
        built = DrugbankTargetSearch(key, Apis.Pubchem, {DrugbankTargetType.target})
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryGeneralFunction(Entry[DrugbankGeneralFunctionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.drugbank:targ-fn"),
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        to: Optional[Path] = CommonArgs.out_annotations_file,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        General functions from DrugBank targets.

        OBJECT: The name of the "general function" (e.g. "Toxic substance binding")

        PREDICATE: "<target_type>:<action>"
        """
        built = DrugbankGeneralFunctionSearch(key, Apis.Pubchem, {DrugbankTargetType.target})
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryDrugbankTransporter(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.drugbank:pk"),
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        to: Optional[Path] = CommonArgs.out_annotations_file,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        PK-related proteins from DrugBank.

        OBJECT: The transporter name (e.g. "Solute carrier family 22 member 11")

        PREDICATE: "<target_type>:<action>" (e.g. metabolized, transported, etc.)
        """
        target_types = {
            DrugbankTargetType.transporter,
            DrugbankTargetType.carrier,
            DrugbankTargetType.enzyme,
        }
        built = DrugbankTargetSearch(key, Apis.Pubchem, target_types)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryTransporterGeneralFunction(Entry[DrugbankGeneralFunctionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.drugbank:pk-fn"),
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        to: Optional[Path] = CommonArgs.out_annotations_file,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        DrugBank PK-related protein functions.

        OBJECT: The name of the general function (e.g. "Toxic substance binding")

        PREDICATE: "<target_type>:<action>" (e.g. metabolized, transported, etc.)
        """
        target_types = {
            DrugbankTargetType.transporter,
            DrugbankTargetType.carrier,
            DrugbankTargetType.enzyme,
        }
        built = DrugbankGeneralFunctionSearch(key, Apis.Pubchem, target_types)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryDrugbankDdi(Entry[DrugbankDdiSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("inter.drugbank:ddi"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Drug/drug interactions listed by DrugBank.

        The "description" column includes useful information about the interaction,
        such as diseases and whether a risk is increased or decreased.

        OBJECT: The name of the drug (e.g. "ibuprofen")

        PREDICATE: typically increase/decrease/change followed by risk/activity/etc.
        """
        built = DrugbankDdiSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryPubchemAssay(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("assay.pubchem:act"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        match_name: bool = EntryArgs.match_name,
        ban_sources: Optional[str] = EntryArgs.banned_sources,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        PubChem bioactivity results.

        Note: The species name, if present, is taken from the target name.
        The taxon ID is what was curated in PubChem.

        OBJECT: The name of the target without species suffix
                (e.g. "Slc6a3 - solute carrier family 6 member 3")

        PREDICATE: "active", "inactive", "inconclusive", or "undetermined"

        WEIGHT: 2 for confirmatory; 1 otherwise
        """
        built = BioactivitySearch(key, Apis.Pubchem, compound_name_must_match=match_name)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryDeaSchedule(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("drug.dea:schedule"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        DEA schedules (PENDING).

        OBJECT: The DEA schedule (1 to 4, or "unscheduled")
        """
        pass


class EntryDeaClass(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("drug.dea:class"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        DEA classes (PENDING).

        OBJECT: The DEA class name (e.g. "hallucinogen")
        """
        pass


class EntryChemidPlusAcute(Entry[AcuteEffectSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("tox.chemidplus:acute"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        level: int = EntryArgs.acute_effect_level,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Acute effect codes from ChemIDPlus.

        OBJECT: The code name (e.g. "behavioral: excitement")
        """
        built = AcuteEffectSearch(
            key,
            Apis.Pubchem,
            top_level=level == 1,
        )
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryChemidPlusLd50(Entry[Ld50Search]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("tox.chemidplus:ld50"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        LD50 acute effects from ChemIDPlus.

        OBJECT: The negative log10 of the dose in mg/kg

        PREDICATE: "LD50:<route>" (e.g. "LD50:intravenous")
        """
        built = Ld50Search(key, Apis.Pubchem)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryG2pInteractions(Entry[G2pInteractionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("g2p:interactions"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Target interactions with affinities from Guide to Pharmacology.

        OBJECT: A molecular target

        PREDICATE: "interaction:agonism", etc.

        WEIGHT: 1.0
        """
        built = G2pInteractionSearch(key, Apis.G2p)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryHmdbTissue(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("hmdb:tissue"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_nm: Optional[float] = EntryArgs.min_nanomolar,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Tissue concentrations from HMDB (PENDING).

        OBJECT:

        PREDICATE: "tissue:..."
        """
        pass


class EntryHmdbComputed(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("hmdb:computed"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        min_nm: Optional[float] = None,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Computed properties from HMDB (PENDING).

        Keys include pKa, logP, logS, etc.

        OBJECT: A number; booleans are converted to 0/1

        PREDICATE: The name of the property
        """
        pass


class EntryPubchemComputed(Entry[ComputedPropertySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("chem.pubchem:computed"),
        keys: str = EntryArgs.pubchem_computed_keys,
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Computed properties from PubChem.

        OBJECT: Number

        PREDICATE: e.g. "complexity"
        """
        # replace acronyms, etc.
        # ComputedPropertySearch standardizes punctuation and casing
        known = {
            k: v
            for k, v in {
                **EntryArgs.KNOWN_USEFUL_KEYS,
                **EntryArgs.KNOWN_USELESS_KEYS,
            }.items()
            if v is not None
        }
        keys = {known.get(s.strip(), s) for s in keys.split(",")}
        built = ComputedPropertySearch(key, Apis.Pubchem, descriptors=keys)
        return cls._run(built, path, to, replace, proceed, check, log, stderr)


class EntryDrugbankAdmet(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("drugbank.admet:properties"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Enzyme predictions from DrugBank (PENDING).

        OBJECT: Enzyme name

        PREDICATE: Action
        """


class EntryDrugbankMetabolites(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("drugbank.admet:metabolites"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Metabolites from DrugBank (PENDING).

        OBJECT: Compound name (e.g. "norcocaine").

        PREDICATE: "metabolized to"
        """


class EntryDrugbankDosage(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("drugbank.admet:dosage"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Dosage from DrugBank (PENDING).

        OBJECT: concentration in mg/mL

        PREDICATE: "dosage :: <route>"

        OTHER COLUMNS:

        - form (e.g. liquid)
        """


class EntryMetaRandom(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.in_compound_table,
        key: str = EntryArgs.key("meta:random"),
        to: Optional[Path] = CommonArgs.out_annotations_file,
        as_of: Optional[str] = CommonArgs.as_of,
        replace: bool = CommonArgs.replace,
        proceed: bool = CommonArgs.proceed,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> Searcher:
        """
        Random class assignment (PENDING).

        OBJECT: 1 thru n-compounds

        PREDICATE: "random"
        """
        pass


Entries = [
    EntryChemblBinding,
    EntryChemblMechanism,
    EntryChemblAtc,
    EntryChemblTrials,
    EntryGoFunction,
    EntryGoProcess,
    EntryGoComponent,
    EntryPubchemComputed,
    EntryPubchemDisease,
    EntryPubchemGeneCoOccurrence,
    EntryPubchemDiseaseCoOccurrence,
    EntryPubchemChemicalCoOccurrence,
    EntryPubchemDgi,
    EntryPubchemCgi,
    EntryDrugbankTarget,
    EntryGeneralFunction,
    EntryDrugbankTransporter,
    EntryTransporterGeneralFunction,
    EntryDrugbankDdi,
    EntryPubchemAssay,
    EntryDeaSchedule,
    EntryDeaClass,
    EntryChemidPlusAcute,
    EntryChemidPlusLd50,
    EntryHmdbTissue,
    EntryMetaRandom,
]
