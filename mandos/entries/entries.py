"""
Run searches and write files.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Optional, TypeVar

from mandos import logger
from mandos.entries._entry_args import EntryArgs
from mandos.entries._entry_utils import EntryUtils
from mandos.entries.abstract_entries import Entry
from mandos.entries.api_singletons import Apis
from mandos.entries.common_args import CommonArgs
from mandos.entries.searcher import Searcher
from mandos.model.utils import ReflectionUtils, InjectionError
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.pubchem_support.pubchem_models import (
    CoOccurrenceType,
    DrugbankTargetType,
)
from mandos.model.searches import Search
from mandos.search.chembl.atc_search import AtcSearch
from mandos.search.chembl.binding_search import BindingSearch
from mandos.search.chembl.go_search import GoSearch
from mandos.model.concrete_hits import GoType
from mandos.search.chembl.indication_search import IndicationSearch
from mandos.search.chembl.mechanism_search import MechanismSearch
from mandos.search.chembl.target_predictions import TargetPredictionSearch
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

S = TypeVar("S", bound=Search, covariant=True)
U = TypeVar("U", covariant=True, bound=CoOccurrenceSearch)


class EntryChemblBinding(Entry[BindingSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("chembl:binding"),
        to: Optional[Path] = CommonArgs.to_single,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal_strategy,
        target_types: str = EntryArgs.target_types,
        confidence: int = EntryArgs.min_confidence,
        binding: float = EntryArgs.binds_cutoff,
        nonbinding: float = EntryArgs.does_not_bind_cutoff,
        relations: str = EntryArgs.relations,
        min_pchembl: float = EntryArgs.min_pchembl,
        banned_flags: str = EntryArgs.banned_flags,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Binding data from ChEMBL.
        These are 'activity' annotations of the type 'B' that have a pCHEMBL value.
        There is extended documentation on this search; see:

        https://mandos-chem.readthedocs.io/en/latest/binding.html

        OBJECT: ChEMBL preferred target name

        PREDICATE: "binding:yes" or "binding:no"

        WEIGHT: pchembl value
        """
        built = BindingSearch(
            key=key,
            api=Apis.Chembl,
            taxa=EntryUtils.get_taxa(taxa),
            traversal=traversal,
            target_types=EntryUtils.get_target_types(target_types),
            min_conf_score=confidence,
            allowed_relations=EntryUtils.split(relations),
            min_pchembl=min_pchembl,
            banned_flags=EntryUtils.get_flags(banned_flags),
            binds_cutoff=binding,
            does_not_bind_cutoff=nonbinding,
        )
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryChemblMechanism(Entry[MechanismSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("chembl:mechanism"),
        to: Optional[Path] = CommonArgs.to_single,
        taxa: Optional[str] = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal_strategy,
        target_types: str = EntryArgs.target_types,
        min_confidence: Optional[int] = EntryArgs.min_confidence,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Mechanism of action (MoA) data from ChEMBL.

        OBJECT: ChEMBL preferred target name

        PREDICATE: Target action; e.g. "agonist" or "positive allosteric modulator"

        WEIGHT: 1.0
        """
        built = MechanismSearch(
            key=key,
            api=Apis.Chembl,
            taxa=EntryUtils.get_taxa(taxa),
            traversal_strategy=traversal,
            allowed_target_types=EntryUtils.get_target_types(target_types),
            min_confidence_score=min_confidence,
        )
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class ChemblQsarPredictions(Entry[TargetPredictionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("chembl:predictions"),
        to: Optional[Path] = CommonArgs.to_single,
        taxa: str = CommonArgs.taxa,
        traversal: str = EntryArgs.traversal_strategy,
        target_types: str = EntryArgs.target_types,
        min_threshold: float = EntryArgs.min_threshold,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Predicted target binding from ChEMBL.

        https://mandos-chem.readthedocs.io/en/latest/binding.html

        OBJECT: ChEMBL preferred target name

        PREDICATE: Either "binding:yes", "binding:no", or "binding:unknown".

        WEIGHT: The sqrt pchembl multiplied by a normalized odds ratio from the confidence set
        """
        built = TargetPredictionSearch(
            key=key,
            api=Apis.Chembl,
            scrape=Apis.ChemblScrape,
            taxa=EntryUtils.get_taxa(taxa),
            traversal=traversal,
            target_types=EntryUtils.get_target_types(target_types),
            min_threshold=min_threshold,
        )
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryChemblTrials(Entry[IndicationSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("chembl:trial"),
        to: Optional[Path] = CommonArgs.to_single,
        min_phase: Optional[int] = EntryArgs.chembl_trial,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Diseases from clinical trials listed in ChEMBL.

        OBJECT: MeSH code

        PREDICATE: "trial"

        WEIGHT: phase (can be 1, 1.5, 2, etc.)
        """
        built = IndicationSearch(key=key, api=Apis.Chembl, min_phase=min_phase)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryChemblAtc(Entry[AtcSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("chembl:atc"),
        to: Optional[Path] = CommonArgs.to_single,
        levels: str = EntryArgs.atc_level,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        ATC codes from ChEMBL.

        OBJECT: ATC Code

        PREDICATE: "ATC L<leveL> code"

        WEIGHT: 1.0
        """
        built = AtcSearch(
            key=key, api=Apis.Chembl, levels={int(x.strip()) for x in levels.split(",")}
        )
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("<see above>"),
        to: Optional[Path] = CommonArgs.to_single,
        taxa: Optional[str] = CommonArgs.taxa,
        traversal_strategy: str = EntryArgs.traversal_strategy,
        target_types: str = EntryArgs.target_types,
        confidence: Optional[int] = EntryArgs.min_confidence,
        relations: str = EntryArgs.relations,
        min_pchembl: float = EntryArgs.min_pchembl,
        banned_flags: Optional[str] = EntryArgs.banned_flags,
        binding_search: Optional[str] = EntryArgs.binding_search_name,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        GO terms associated with ChEMBL binding targets.

        OBJECT: GO Term name

        PREDICATE: "go:<type>"

        WEIGHT: pchembl value

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
                taxa=EntryUtils.get_taxa(taxa),
                traversal=traversal_strategy,
                target_types=EntryUtils.get_target_types(target_types),
                min_conf_score=confidence,
                allowed_relations=EntryUtils.split(relations),
                min_pchembl=min_pchembl,
                banned_flags=EntryUtils.get_flags(banned_flags),
            )
        except (TypeError, ValueError):
            raise InjectionError(f"Failed to build {binding_clazz.__qualname__}")
        built = GoSearch(key, api, cls.go_type(), binding_search)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("disease.ctd:mesh"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Diseases in the CTD.

        Comparative Toxicogenomics Database.

        OBJECT: MeSH code of disease

        PREDICATE: "disease:marker/mechanism", etc.

        WEIGHT: depends on the evidence type
        """
        built = DiseaseSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("<see above>"),
        to: Optional[Path] = CommonArgs.to_single,
        min_score: float = EntryArgs.min_cooccurrence_score,
        min_articles: int = EntryArgs.min_cooccurring_articles,
        as_of: Optional[str] = CommonArgs.as_of,
        log: Optional[Path] = CommonArgs.log_path,
        check: bool = EntryArgs.check,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Co-occurrences from PubMed articles.
        There is extended documentation on this search.
        Also refer to https://pubchemdocs.ncbi.nlm.nih.gov/knowledge-panels

        OBJECT: Name of gene/chemical/disease

        PREDICATE: "co-occurrence:<gene/chemical/disease>"

        WEIGHT: enrichment score; see PubChem docs
        """
        if key is None or key == "<see above>":
            key = cls.cmd()
        clazz = cls.get_search_type()
        built = clazz(key, Apis.Pubchem, min_score=min_score, min_articles=min_articles)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryPubchemGeneCoOccurrence(_EntryPubchemCoOccurrence[GeneCoOccurrenceSearch]):
    """ """


class EntryPubchemDiseaseCoOccurrence(_EntryPubchemCoOccurrence[DiseaseCoOccurrenceSearch]):
    """ """


class EntryPubchemChemicalCoOccurrence(_EntryPubchemCoOccurrence[ChemicalCoOccurrenceSearch]):
    """ """


class EntryPubchemDgi(Entry[DgiSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.dgidb:gene"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        log: Optional[Path] = CommonArgs.log_path,
        check: bool = EntryArgs.check,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Drug/gene interactions in the DGIDB.

        Drug Gene Interaction Database.
        Also see ``disease.dgidb:int``.

        OBJECT: Name of the gene

        PREDICATE: "interaction:generic" or "interaction:<type>"

        WEIGHT: 1.0
        """
        built = DgiSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryPubchemCgi(Entry[CtdGeneSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.ctd:gene"),
        as_of: Optional[str] = CommonArgs.as_of,
        to: Optional[Path] = CommonArgs.to_single,
        log: Optional[Path] = CommonArgs.log_path,
        check: bool = EntryArgs.check,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Compound/gene interactions in the DGIDB.

        Drug Gene Interaction Database.
        Also see ``interact.dgidb:int``.

        OBJECT: Name of the gene

        PREDICATE: derived from the interaction type (e.g. downregulation)

        WEIGHT: 1.0
        """
        built = CtdGeneSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryDrugbankTarget(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.drugbank:targ"),
        as_of: Optional[str] = CommonArgs.as_of,
        to: Optional[Path] = CommonArgs.to_single,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Protein targets from DrugBank.

        OBJECT: Target name (e.g. "Solute carrier family 22 member 11") from DrugBank

        PREDICATE: "<target_type>:<action>"
        """
        built = DrugbankTargetSearch(key, Apis.Pubchem, {DrugbankTargetType.target})
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryGeneralFunction(Entry[DrugbankGeneralFunctionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.drugbank:targ-fn"),
        as_of: Optional[str] = CommonArgs.as_of,
        to: Optional[Path] = CommonArgs.to_single,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        General functions from DrugBank targets.

        OBJECT: Name of the general function (e.g. "Toxic substance binding")

        PREDICATE: "<target_type>:<action>"
        """
        built = DrugbankGeneralFunctionSearch(key, Apis.Pubchem, {DrugbankTargetType.target})
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryDrugbankTransporter(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.drugbank:pk"),
        as_of: Optional[str] = CommonArgs.as_of,
        to: Optional[Path] = CommonArgs.to_single,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        PK-related proteins from DrugBank.

        OBJECT: Transporter name (e.g. "Solute carrier family 22 member 11") from DrugBank

        PREDICATE: "<target_type>:<action>" (e.g. metabolized, transported, etc.)
        """
        target_types = {
            DrugbankTargetType.transporter,
            DrugbankTargetType.carrier,
            DrugbankTargetType.enzyme,
        }
        built = DrugbankTargetSearch(key, Apis.Pubchem, target_types)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryTransporterGeneralFunction(Entry[DrugbankGeneralFunctionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.drugbank:pk-fn"),
        as_of: Optional[str] = CommonArgs.as_of,
        to: Optional[Path] = CommonArgs.to_single,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        DrugBank PK-related protein functions.

        OBJECT: Name of the general function (e.g. "Toxic substance binding")

        PREDICATE: "<target_type>:<action>" (e.g. metabolized, transported, etc.)
        """
        target_types = {
            DrugbankTargetType.transporter,
            DrugbankTargetType.carrier,
            DrugbankTargetType.enzyme,
        }
        built = DrugbankGeneralFunctionSearch(key, Apis.Pubchem, target_types)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryDrugbankDdi(Entry[DrugbankDdiSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("inter.drugbank:ddi"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Drug/drug interactions listed by DrugBank.

        The 'description' column includes useful information about the interaction,
        such as diseases and whether a risk is increased or decreased.

        OBJECT: name of the drug (e.g. "ibuprofen")

        PREDICATE: typically increase/decrease/change followed by risk/activity/etc.
        """
        built = DrugbankDdiSearch(key, Apis.Pubchem)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryPubchemAssay(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("assay.pubchem:act"),
        to: Optional[Path] = CommonArgs.to_single,
        name_must_match: bool = EntryArgs.name_must_match,
        ban_sources: Optional[str] = None,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        PubChem bioactivity results.

        Note: The species name, if present, is taken from the target name.
        The taxon ID is what was curated in PubChem.

        OBJECT: Name of the target without species suffix (e.g. "Slc6a3 - solute carrier family 6 member 3")

        PREDICATE: "active"|"inactive"|"inconclusive"|"undetermined"

        WEIGHT: 2 for confirmatory; 1 otherwise
        """
        built = BioactivitySearch(key, Apis.Pubchem, compound_name_must_match=name_must_match)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryDeaSchedule(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("drug.dea:schedule"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        DEA schedules (PENDING).

        OBJECT: (1 to 4, or "unscheduled")

        PREDICATE: "dea:schedule"

        WEIGHT: 1.0
        """
        pass


class EntryDeaClass(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("drug.dea:class"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        DEA classes (PENDING).

        OBJECT: e.g. "hallucinogen"

        PREDICATE: "dea:class"

        WEIGHT: 1.0
        """
        pass


class EntryChemidPlusAcute(Entry[AcuteEffectSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("tox.chemidplus:acute"),
        to: Optional[Path] = CommonArgs.to_single,
        level: int = EntryArgs.acute_effect_level,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Acute effect codes from ChemIDPlus.

        OBJECT: E.g. "behavioral: excitement"

        PREDICATE: "effect:acute"

        WEIGHT: 1.0
        """
        built = AcuteEffectSearch(
            key,
            Apis.Pubchem,
            top_level=level == 1,
        )
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryChemidPlusLd50(Entry[Ld50Search]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("tox.chemidplus:ld50"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        LD50 acute effects from ChemIDPlus.

        OBJECT: A dose in mg/kg (e.g. 3100)

        PREDICATE: "LD50::<route>" (e.g. "LD50::intravenous)

        WEIGHT: 1.0
        """
        built = Ld50Search(key, Apis.Pubchem)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryG2pInteractions(Entry[G2pInteractionSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("g2p:interactions"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
    ) -> Searcher:
        """
        Target interactions with affinities from Guide to Pharmacology.

        OBJECT: A molecular target

        PREDICATE: "interaction:agonism", etc.

        WEIGHT: 1.0
        """
        built = G2pInteractionSearch(key, Apis.G2p)
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryHmdbTissue(Entry[BioactivitySearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("hmdb:tissue"),
        to: Optional[Path] = CommonArgs.to_single,
        min_nanomolar: Optional[float] = None,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("hmdb:computed"),
        to: Optional[Path] = CommonArgs.to_single,
        min_nanomolar: Optional[float] = None,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("chem.pubchem:computed"),
        keys: str = EntryArgs.pubchem_computed_keys,
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
        return cls._run(built, path, to, check, log, quiet, verbose, no_setup)


class EntryDrugbankAdmet(Entry[DrugbankTargetSearch]):
    @classmethod
    def run(
        cls,
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("drugbank.admet:properties"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("drugbank.admet:metabolites"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("drugbank.admet:dosage"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
        path: Path = CommonArgs.compounds,
        key: str = EntryArgs.key("meta:random"),
        to: Optional[Path] = CommonArgs.to_single,
        as_of: Optional[str] = CommonArgs.as_of,
        check: bool = EntryArgs.check,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        no_setup: bool = CommonArgs.no_setup,
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
