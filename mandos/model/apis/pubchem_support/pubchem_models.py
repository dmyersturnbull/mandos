from __future__ import annotations

import enum
import typing
from dataclasses import dataclass
from datetime import date
from typing import FrozenSet, Mapping, Optional, Sequence, Set, Union

import orjson
import regex
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import XTypeError, XValueError
from pocketutils.tools.string_tools import StringTools

from mandos.model.utils.resources import MandosResources
from mandos.model.apis.pubchem_support._nav_fns import Mapx


hazards = MandosResources.path("hazards.json").read_text(encoding="utf8")
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
        if isinstance(value, float):
            try:
                value = int(value)
                value = StringTools.strip_off_end(str(value).strip(), ".0")
            except ArithmeticError:
                value = str(value)
                value = StringTools.strip_off_end(str(value).strip(), ".0")
        value = str(value).strip()
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


class CoOccurrenceType(enum.Enum):
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


class ClinicalTrialsGovUtils:
    @classmethod
    def phase_map(cls) -> Mapping[str, float]:
        return {
            "Phase 4": 4,
            "Phase 3": 3,
            "Phase 2": 2,
            "Phase 1": 1,
            "Early Phase 1": 1.5,
            "Phase 2/Phase 3": 2.5,
            "N/A": 0,
        }

    @classmethod
    def known_phases(cls) -> Set[float]:
        return set(cls.phase_map().values())

    @classmethod
    def resolve_statuses(cls, st: str) -> Set[str]:
        found = set()
        for s in st.lower().split(","):
            s = s.strip()
            if s == "@all":
                match = cls.known_statuses()
            elif s in cls.known_statuses():
                match = {s}
            else:
                raise XValueError(f"Invalid status {s}")
            for m in match:
                found.add(m)
        return found

    @classmethod
    def known_statuses(cls) -> Set[str]:
        return set(cls.status_map().values())

    @classmethod
    def status_map(cls) -> Mapping[str, str]:
        return {
            "Unknown status": "unknown",
            "Completed": "completed",
            "Terminated": "stopped",
            "Suspended": "stopped",
            "Withdrawn": "stopped",
            "Not yet recruiting": "ongoing",
            "Recruiting": "ongoing",
            "Enrolling by invitation": "ongoing",
            "Active, not recruiting": "ongoing",
            "Available": "completed",
            "No longer available": "completed",
            "Temporarily not available": "completed",
            "Approved for marketing": "completed",
        }


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
    def mapped_phase(self) -> float:
        return ClinicalTrialsGovUtils.phase_map().get(self.phase, 0)

    @property
    def mapped_status(self) -> str:
        return ClinicalTrialsGovUtils.status_map().get(self.status, "unknown")


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
        # TODO: Could it ever start with just a dot; e.g. '.175'?
        match = regex.compile(r".+?\((\d+(?:.\d+)?) *mg/kg\)").fullmatch(self.dose, flags=regex.V1)
        if match is None:
            raise XValueError(f"Dose {self.dose} (acute effect {self.gid}) could not be parsed")
        return float(match.group(1))


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
        pat = regex.compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?", flags=regex.V1)
        match = pat.fullmatch(self.code)
        return [g for g in match.groups() if g is not None]


class DrugbankTargetType(enum.Enum):
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


class Activity(enum.Enum):
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
    def target_name_abbrev_species(self) -> typing.Tuple[Optional[str], str, Optional[str]]:
        # first, look for a species name in parentheses
        # We use \)+ at the end instead of \)
        # this is to catch cases where we have parentheses inside of the species name
        # this happens with some virus strains, for e.g.
        match = regex.compile(r"^(.+?)\(([^)]+)\)+$", flags=regex.V1).fullmatch(self.target_name)
        if match is None:
            species = None
            target = self.target_name
        else:
            species = match.group(2)
            target = match.group(1)
        # now try to get an abbreviation
        match = regex.compile(r"^ *([^ ]+) +- +(.+)$, flags=regex.V1").fullmatch(target)
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
    "ClinicalTrialsGovUtils",
    "AcuteEffectEntry",
    "DrugbankTargetType",
]
