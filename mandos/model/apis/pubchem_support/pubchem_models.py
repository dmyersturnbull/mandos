from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from typing import (
    AbstractSet,
    FrozenSet,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import orjson
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.enums import CleverEnum
from pocketutils.core.exceptions import XTypeError, XValueError
from pocketutils.tools.string_tools import StringTools

from mandos.model.apis.pubchem_support._nav_fns import Mapx
from mandos.model.apis.pubchem_support._patterns import Patterns
from mandos.model.utils.setup import MandosResources

hazards = MandosResources.file("hazards.json").read_text(encoding="utf8")
hazards = NestedDotDict(orjson.loads(hazards))
hazards = {d["code"]: d for d in hazards["signals"]}


@dataclass(frozen=True, repr=True, eq=True, order=True)
class ComputedProperty:
    key: str
    value: Union[int, str, float, bool]
    unit: Optional[str]
    ref: str

    def req_is(self, type_) -> Union[int, str, float, bool]:
        if not isinstance(self.value, type_):
            raise XTypeError(f"{self.key}->{self.value} has {type(self.value)}, not {type_}")
        return self.value

    @property
    def as_str(self) -> str:
        return f"{self.value} {self.unit}"


class Code(str):
    @property
    def type_name(self) -> str:
        return self.__class__.__name__.lower()

    @classmethod
    def of(cls, value: Union[str, int, float]) -> __qualname__:
        value = StringTools.strip_off_end(str(value).strip(), ".0").strip()
        return cls(value)

    @classmethod
    def of_nullable(cls, value: Union[None, str, int, float]) -> Optional[__qualname__]:
        if value is None:
            return None
        return cls.of(value)


class Codes:
    """
    These turn out to be extremely useful for documenting return types.
    For example, ``DrugbankInteraction`` might have a ``gene`` field,
    which can be described as a ``GenecardSymbol`` if known.
    """

    class ChemIdPlusOrganism(Code):
        """
        E.g. 'women', 'frog', 'infant', or 'domestic animals - goat/sheep'
        """

        @property
        def is_human(self) -> bool:
            return str(self) in {"women", "woman", "men", "man", "infant", "infants", "human"}

    class ChemIdPlusEffect(Code):
        """
        E.g. 'BEHAVIORAL: MUSCLE WEAKNESS'
        """

        @property
        def category(self) -> str:
            return self[: self.index(":")].strip()

        @property
        def subcategory(self) -> str:
            return self[self.index(":") + 1 :].strip()

    class EcNumber(Code):
        """
        e.g. 'EC:4.6.1.1'
        """

    class GeneId(Code):
        """
        GeneCard, UniProt gene name, etc.
        e.g. 'slc1a2'
        """

    class ClinicaltrialId(Code):
        """
        From clinicaltrials.gov
        """

    class GenericDiseaseCode(Code):
        """
        From clinicaltrials.gov; pure int
        """

    class GenecardSymbol(GeneId):
        """ """

    class UniprotId(GeneId):
        """ """

    class PubchemCompoundId(Code):
        """
        e.g. 2352
        """

        @property
        def value(self) -> int:
            return int(self)

    class AtcCode(Code):
        """ """

    class PubmedId(Code):
        """ """

    class Doi(Code):
        """ """

    class MeshCode(Code):
        """ """

    class PdbId(Code):
        """ """

    class MeshHeading(Code):
        """ """

    class MeshSubheading(Code):
        """ """

    class DrugbankCompoundId(Code):
        """ """

    class DeaSchedule(Code):
        """ """

        @property
        def value(self) -> int:
            return Mapx.roman_to_arabic(1, 5)(self)

    class GhsCode(Code):
        """ """


class CoOccurrenceType(CleverEnum):
    chemical = enum.auto()
    gene = enum.auto()
    disease = enum.auto()

    @property
    def x_name(self) -> str:
        if self is CoOccurrenceType.chemical:
            return "ChemicalNeighbor"
        elif self is CoOccurrenceType.gene:
            return "ChemicalGeneSymbolNeighbor"
        elif self is CoOccurrenceType.disease:
            return "ChemicalDiseaseNeighbor"
        raise AssertionError(f"{self} not found!!")

    @property
    def id_name(self) -> str:
        if self is CoOccurrenceType.chemical:
            return "CID"
        elif self is CoOccurrenceType.gene:
            return "GeneSymbol"
        elif self is CoOccurrenceType.disease:
            return "MeSH"
        raise AssertionError(f"{self} not found!!")


class _PM(NamedTuple):
    name: str
    score: float


class _SM(NamedTuple):
    name: str
    simplified: str


_phase_map: Mapping[str, _PM] = dict(
    phase_4=_PM("Phase 4", 4),
    phase_3=_PM("Phase 3", 3),
    phase_2=_PM("Phase 2", 2),
    phase_1=_PM("Phase 1", 1),
    early_phase_1=_PM("Early Phase 1", 0.5),
    phase_2_or_3=_PM("Phase 2/Phase 3", 2.5),
    na=_PM("N/A", 0.5),
    unknown=_PM("", 0.5),  # doesn't occur in the wild
)
_status_map: Mapping[str, _SM] = dict(
    unknown=_SM("Unknown status", "unknown"),
    completed=_SM("Completed", "completed"),
    terminated=_SM("Terminated", "stopped"),
    suspended=_SM("Suspended", "stopped"),
    withdrawn=_SM("Withdrawn", "stopped"),
    not_yet_recruiting=_SM("Not yet recruiting", "ongoing"),
    recruiting=_SM("Recruiting", "ongoing"),
    enrolling_by_invitation=_SM("Enrolling by invitation", "ongoing"),
    active_not_recruiting=_SM("Active, not recruiting", "ongoing"),
    available=_SM("Available", "completed"),
    no_longer_available=_SM("No longer available", "completed"),
    temporarily_not_available=_SM("Temporarily not available", "completed"),
    approved_for_marketing=_SM("Approved for marketing", "completed"),
)


class ClinicalTrialSimplifiedStatus(CleverEnum):
    unknown = ()
    completed = ()
    stopped = ()
    ongoing = ()

    @classmethod
    def parse(cls, st: str) -> AbstractSet[ClinicalTrialSimplifiedStatus]:
        _mp = {"@all": set(cls)}
        found: Set[ClinicalTrialSimplifiedStatus] = set()
        for s in st.lower().split(","):
            found.update(_mp.get(s.strip(), {s.strip()}))
        return found


class ClinicalTrialPhase(CleverEnum):
    unknown = ()
    na = ()
    phase_2_or_3 = ()
    early_phase_1 = ()
    phase_1 = ()
    phase_2 = ()
    phase_3 = ()
    phase_4 = ()

    @classmethod
    def _unmatched_type(cls) -> Optional[__qualname__]:
        return cls.unknown

    @classmethod
    def parse(cls, st: str) -> AbstractSet[ClinicalTrialPhase]:
        _by_score = {"@" + str(v): {x for x in cls if x.score == v} for v in {x.score for x in cls}}
        _map = {**{"@all": set(cls)}, **_by_score}
        found: Set[ClinicalTrialPhase] = set()
        for s in [s.strip() for s in st.lower().split(",")]:
            found.update(_map.get(s, {cls[s]}))
        return found

    @classmethod
    def of(cls, s: Union[str, __qualname__]) -> __qualname__:
        if isinstance(s, str):
            s = _phase_map.get(s, _PM(s, -1)).name
        return super().of(s)

    @property
    def raw_name(self) -> str:
        return _phase_map[self.name].name

    @property
    def score(self) -> float:
        return _phase_map[self.name].score


class ClinicalTrialStatus(CleverEnum):

    unknown = ()
    completed = ()
    terminated = ()
    suspended = ()
    withdrawn = ()
    not_yet_recruiting = ()
    recruiting = ()
    enrolling_by_invitation = ()
    active_not_recruiting = ()
    available = ()
    no_longer_available = ()
    temporarily_not_available = ()
    approved_for_marketing = ()

    @classmethod
    def _unmatched_type(cls) -> Optional[__qualname__]:
        return cls.unknown

    @classmethod
    def parse(cls, st: str) -> AbstractSet[ClinicalTrialStatus]:
        _by_simple = {
            "@" + v: {x for x in cls if x.simplified.name == v}
            for v in {x.simplified.name for x in cls}
        }
        _map = {**{"@all": set(cls)}, **_by_simple}
        found: Set[ClinicalTrialStatus] = set()
        for s in [s.strip() for s in st.lower().split(",")]:
            found.update(_map.get(s, {cls[s]}))
        return found

    @classmethod
    def of(cls, s: Union[str, __qualname__]) -> __qualname__:
        if isinstance(s, str):
            s = _status_map.get(s, _SM(s, "--")).name
        return super().of(s)

    @property
    def raw_name(self) -> str:
        return _status_map[self.name][0]

    @property
    def simplified(self) -> ClinicalTrialSimplifiedStatus:
        return _status_map[self.name][1]


@dataclass(frozen=True, repr=True, eq=True)
class ClinicalTrial:
    ctid: Codes.ClinicaltrialId
    title: str
    conditions: FrozenSet[str]
    disease_ids: FrozenSet[Codes.ClinicaltrialId]
    phase: str
    status: str
    interventions: FrozenSet[str]
    cids: FrozenSet[Codes.PubchemCompoundId]
    source: str

    @property
    def mapped_phase(self) -> ClinicalTrialPhase:
        return ClinicalTrialPhase.of(self.phase)

    @property
    def mapped_status(self) -> ClinicalTrialStatus:
        return ClinicalTrialStatus.of(self.status)


@dataclass(frozen=True, repr=True, eq=True)
class GhsCode:
    code: Codes.GhsCode
    statement: str
    clazz: str
    categories: FrozenSet[str]
    signal_word: str
    type: str

    @classmethod
    def find(cls, code: str) -> GhsCode:
        h = hazards[code]
        cats = h["category"]  # TODO
        return GhsCode(
            code=Codes.GhsCode(code),
            statement=h["statement"],
            clazz=h["class"],
            categories=cats,
            signal_word=h["signal_word"],
            type=h["type"],
        )

    @property
    def level(self) -> int:
        return int(self.code[1])


@dataclass(frozen=True, repr=True, eq=True)
class AcuteEffectEntry:
    gid: int
    effects: FrozenSet[Codes.ChemIdPlusEffect]
    organism: Codes.ChemIdPlusOrganism
    test_type: str
    route: str
    dose: str

    @property
    def mg_per_kg(self) -> float:
        match = Patterns.mg_per_kg_pattern.search(self.dose)
        if match is None:
            # e.g. mg/m3/2H (mass per liter per time)
            raise XValueError(f"Dose {self.dose} (acute effect {self.gid}) could not be parsed")
        scale = dict(g=1e3, gm=1e3, mg=1, ug=10e-3, ng=10e-6, pg=10e-9)[match.group(2)]
        return float(match.group(1)) * scale


@dataclass(frozen=True, repr=True, eq=True)
class AssociatedDisorder:
    gid: str
    disease_id: Codes.MeshCode
    disease_name: str
    evidence_type: str
    n_refs: int


@dataclass(frozen=True, repr=True, eq=True)
class AtcCode:
    code: str
    name: str

    @property
    def level(self) -> int:
        return len(self.parts)

    @property
    def parts(self) -> Sequence[str]:
        match = Patterns.atc_parts_pattern.fullmatch(self.code)
        return [g for g in match.groups() if g is not None]


class DrugbankTargetType(CleverEnum):
    target = enum.auto()
    carrier = enum.auto()
    transporter = enum.auto()
    enzyme = enum.auto()


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankInteraction:
    record_id: Optional[str]
    gene_symbol: Codes.GeneId
    action: Optional[str]
    protein_id: str
    target_type: DrugbankTargetType
    target_name: str
    general_function: Optional[str]
    specific_function: str
    pmids: FrozenSet[Codes.PubmedId]
    dois: FrozenSet[Codes.Doi]


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankDdi:
    drug_drugbank_id: Codes.DrugbankCompoundId
    drug_pubchem_id: Codes.PubchemCompoundId
    drug_drugbank_name: str
    description: str


class Activity(CleverEnum):
    active = enum.auto()
    inactive = enum.auto()
    inconclusive = enum.auto()
    unspecified = enum.auto()


@dataclass(frozen=True, repr=True, eq=True)
class Bioactivity:
    assay_id: int
    assay_type: str
    assay_ref: str
    assay_name: str
    assay_made_date: date
    gene_id: Optional[Codes.GeneId]
    tax_id: Optional[int]
    pmid: Optional[Codes.PubmedId]
    activity: Optional[Activity]
    activity_name: Optional[str]
    activity_value: Optional[float]
    target_name: Optional[str]
    compound_name: str

    @property
    def target_name_abbrev_species(self) -> Tuple[Optional[str], str, Optional[str]]:
        # first, look for a species name in parentheses
        # We use \)+ at the end instead of \)
        # this is to catch cases where we have parentheses inside of the species name
        # this happens with some virus strains, for e.g.
        match = Patterns.target_name_abbrev_species_pattern_1.fullmatch(self.target_name)
        if match is None:
            species = None
            target = self.target_name
        else:
            species = match.group(2)
            target = match.group(1)
        # now try to get an abbreviation
        match = Patterns.target_name_abbrev_species_pattern_2.fullmatch(target)
        if match is None:
            abbrev = None
            name = target
        else:
            abbrev = match.group(1)
            name = match.group(2)
        return name, abbrev, species


@dataclass(frozen=True, repr=True, eq=True)
class PdbEntry:
    pdbid: Codes.PdbId
    title: str
    exp_method: str
    resolution: float
    lig_names: FrozenSet[str]
    cids: FrozenSet[Codes.PubchemCompoundId]
    uniprot_ids: FrozenSet[Codes.UniprotId]
    pmids: FrozenSet[Codes.PubmedId]
    dois: FrozenSet[Codes.Doi]


@dataclass(frozen=True, repr=True, eq=True)
class PubmedEntry:
    pmid: Codes.PubmedId
    article_type: str
    pmidsrcs: FrozenSet[str]
    mesh_headings: FrozenSet[Codes.MeshHeading]
    mesh_subheadings: FrozenSet[Codes.MeshSubheading]
    mesh_codes: FrozenSet[Codes.MeshCode]
    cids: FrozenSet[Codes.PubchemCompoundId]
    article_title: str
    article_abstract: str
    journal_name: str
    pub_date: date


@dataclass(frozen=True, repr=True, eq=True)
class Publication:
    pmid: Codes.PubmedId
    pub_date: date
    is_review: bool
    title: str
    journal: str
    relevance_score: int


@dataclass(frozen=True, repr=True, eq=True)
class CoOccurrence:
    neighbor_id: str
    neighbor_name: str
    kind: CoOccurrenceType
    # https://pubchemdocs.ncbi.nlm.nih.gov/knowledge-panels
    article_count: int
    query_article_count: int
    neighbor_article_count: int
    score: int
    publications: FrozenSet[Publication]

    def strip_pubs(self) -> CoOccurrence:
        return CoOccurrence(
            self.neighbor_id,
            self.neighbor_name,
            self.kind,
            self.article_count,
            self.query_article_count,
            self.neighbor_article_count,
            self.score,
            frozenset({}),
        )


@dataclass(frozen=True, repr=True, eq=True)
class DrugGeneInteraction:
    """ """

    gene_name: Optional[str]
    gene_claim_id: Optional[str]
    source: str
    interactions: FrozenSet[str]
    pmids: FrozenSet[Codes.PubmedId]
    dois: FrozenSet[Codes.Doi]


@dataclass(frozen=True, repr=True, eq=True)
class ChemicalGeneInteraction:
    gene_name: Optional[Codes.GeneId]
    interactions: FrozenSet[str]
    tax_id: Optional[int]
    tax_name: Optional[str]
    pmids: FrozenSet[Codes.PubmedId]


__all__ = [
    "ClinicalTrial",
    "AssociatedDisorder",
    "AtcCode",
    "DrugbankInteraction",
    "DrugbankDdi",
    "Bioactivity",
    "Activity",
    "DrugGeneInteraction",
    "ChemicalGeneInteraction",
    "GhsCode",
    "PubmedEntry",
    "Code",
    "Codes",
    "CoOccurrenceType",
    "CoOccurrence",
    "Publication",
    "ComputedProperty",
    "ClinicalTrialStatus",
    "ClinicalTrialSimplifiedStatus",
    "ClinicalTrialPhase",
    "AcuteEffectEntry",
    "DrugbankTargetType",
]
