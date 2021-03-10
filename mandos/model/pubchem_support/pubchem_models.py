from __future__ import annotations
import enum
import re
from dataclasses import dataclass
from datetime import date
from typing import Union, Optional, FrozenSet, Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.utils import MandosResources
from mandos.model.pubchem_support._nav_fns import Mapx

hazards = {
    d["code"]: d for d in NestedDotDict.read_toml(MandosResources.path("hazards.toml"))["signals"]
}


@dataclass(frozen=True, repr=True, eq=True, order=True)
class ComputedProperty:
    key: str
    value: Union[int, str, float, bool]
    unit: Optional[str]
    ref: str

    def req_is(self, type_) -> Union[int, str, float, bool]:
        if not isinstance(self.value, type_):
            raise TypeError(f"{self.key}->{self.value} has {type(self.value)}, not {type_}")
        return self.value

    @property
    def as_str(self) -> str:
        return f"{self.value} {self.unit}"


class Code(str):
    @property
    def type_name(self) -> str:
        return self.__class__.__name__.lower()

    @classmethod
    def of(cls, value: Union[str, int, float]):
        if isinstance(value, float):
            try:
                value = int(value)
            except ArithmeticError:
                value = str(value)
        value = str(value).strip()
        return cls(value)


class Codes:
    """
    These turn out to be extremely useful for documenting return types.
    For example, ``DrugbankInteraction`` might have a ``gene`` field,
    which can be described as a ``GenecardSymbol`` if known.
    """

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
        """"""

    class UniprotId(GeneId):
        """"""

    class PubchemCompoundId(Code):
        """
        e.g. 2352
        """

        @property
        def value(self) -> int:
            return int(self)

    class AtcCode(Code):
        """"""

    class PubmedId(Code):
        """"""

    class Doi(Code):
        """"""

    class MeshCode(Code):
        """"""

    class PdbId(Code):
        """"""

    class MeshHeading(Code):
        """"""

    class MeshSubheading(Code):
        """"""

    class DrugbankCompoundId(Code):
        """"""

    class DeaSchedule(Code):
        """"""

        @property
        def value(self) -> int:
            return Mapx.roman_to_arabic(1, 5)(self)

    class GhsCode(Code):
        """"""


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
    def known_phase(self) -> int:
        return {
            "Phase 4": 4,
            "Phase 3": 3,
            "Phase 2": 2,
            "Phase 1": 1,
            "Early Phase 1": 1,
            "Phase 2/Phase 3": 2,
            "N/A": 0,
        }.get(self.phase, 0)

    @property
    def known_status(self) -> str:
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
        }.get(self.status, "unknown")


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
        pat = re.compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?")
        match = pat.fullmatch(self.code)
        return [g for g in match.groups() if g is not None]


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankInteraction:
    gene_symbol: Codes.GeneId
    action: str
    target_name: str
    general_function: Sequence[str]
    specific_function: str
    pmids: FrozenSet[Codes.PubmedId]
    dois: FrozenSet[Codes.Doi]


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankDdi:
    drug_drugbank_id: Codes.DrugbankCompoundId
    drug_pubchem_id: Codes.PubchemCompoundId
    drug_drugbank_name: str
    description: str


class AssayType(enum.Enum):
    confirmatory = enum.auto()
    literature = enum.auto()


class Activity(enum.Enum):
    active = enum.auto()
    inactive = enum.auto()
    unspecified = enum.auto()


@dataclass(frozen=True, repr=True, eq=True)
class Bioactivity:
    assay_id: int
    assay_type: AssayType
    assay_ref: str
    assay_name: str
    assay_made_date: date
    gene_id: Optional[Codes.GeneId]
    tax_id: Optional[int]
    pmid: Optional[Codes.PubmedId]
    activity: Optional[Activity]
    activity_name: Optional[str]
    activity_value: float
    target_name: Optional[str]


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
    """"""

    gene_name: Optional[str]
    gene_claim_id: Optional[str]
    source: str
    interactions: FrozenSet[str]
    pmids: FrozenSet[Codes.PubmedId]
    dois: FrozenSet[Codes.Doi]


@dataclass(frozen=True, repr=True, eq=True)
class CompoundGeneInteraction:
    gene_name: Optional[Codes.GeneId]
    interactions: FrozenSet[str]
    tax_name: Optional[str]
    pmids: FrozenSet[Codes.PubmedId]


__all__ = [
    "ClinicalTrial",
    "AssociatedDisorder",
    "AtcCode",
    "AssayType",
    "DrugbankInteraction",
    "DrugbankDdi",
    "Bioactivity",
    "Activity",
    "DrugGeneInteraction",
    "CompoundGeneInteraction",
    "GhsCode",
    "PubmedEntry",
    "Code",
    "Codes",
    "CoOccurrenceType",
    "CoOccurrence",
    "Publication",
    "ComputedProperty",
]
