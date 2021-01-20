from __future__ import annotations
import enum
import re
from dataclasses import dataclass
from datetime import date
from typing import Union, Optional, FrozenSet, Sequence

import pandas as pd

from mandos import MandosResources
from mandos.model.query_utils import Fns

hazards = pd.read_csv(MandosResources.path("hazards.tab"), sep="\t")
hazards = dict(hazards.set_index("code").T.to_dict())


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


class CodeTypes:
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

    class GenecardSymbol(GeneId):
        """"""

    class PubchemCompoundId(Code):
        """
        e.g. 2352
        """

        @property
        def value(self) -> int:
            return int(self)

    class MeshCode(Code):
        """"""

    class PdbId(Code):
        """"""

    class MeshHeading(Code):
        """"""

    class MeshSubheading(Code):
        """"""

    class DeaSchedule(Code):
        """"""

        @property
        def value(self) -> int:
            return Fns.roman_to_arabic(1, 5)(self)

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
    title: str
    conditions: FrozenSet[str]
    phase: str
    status: str
    interventions: FrozenSet[str]
    cids: FrozenSet[int]
    source: str

    @property
    def known_phase(self) -> int:
        return {
            "Phase 4": 4,
            "Phase 3": 3,
            "Phase 2": 2,
            "Phase 1": 1,
            "Early Phase 1": 1,
            "N/A": 0,
        }.get(self.status, 0)


@dataclass(frozen=True, repr=True, eq=True)
class GhsCode:
    code: CodeTypes.GhsCode
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
            code=CodeTypes.GhsCode(code),
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
    disease: str
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
    action: str
    target: str
    gene: str
    function: str
    n_refs: int


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankDdi:
    is_active: bool
    micromolar: float
    activity_type: str
    target: str


@dataclass(frozen=True, repr=True, eq=True)
class PubchemBioassay:
    drug: str
    interaction: str


@dataclass(frozen=True, repr=True, eq=True)
class PdbEntry:
    pdbid: str
    title: str
    exp_method: str
    resolution: float
    lig_names: FrozenSet[str]
    cids: FrozenSet[int]
    uniprot_ids: FrozenSet[str]
    pmids: FrozenSet[str]
    dois: FrozenSet[str]


@dataclass(frozen=True, repr=True, eq=True)
class PubmedEntry:
    pmid: int
    article_type: str
    pmidsrcs: FrozenSet[str]
    mesh_headings: FrozenSet[CodeTypes.MeshHeading]
    mesh_subheadings: FrozenSet[CodeTypes.MeshSubheading]
    mesh_codes: FrozenSet[CodeTypes.MeshCode]
    cids: FrozenSet[int]
    article_title: str
    article_abstract: str
    journal_name: str
    pub_date: date


@dataclass(frozen=True, repr=True, eq=True)
class Publication:
    pmid: int
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


@dataclass(frozen=True, repr=True, eq=True)
class DrugGeneInteraction:
    """"""

    gene_name: Optional[str]
    gene_claim_id: Optional[str]
    source: str
    interactions: FrozenSet[str]
    pmids: FrozenSet[str]
    dois: FrozenSet[str]


@dataclass(frozen=True, repr=True, eq=True)
class CompoundGeneInteraction:
    gene_name: Optional[str]
    interactions: FrozenSet[str]
    tax_name: Optional[str]
    pmids: FrozenSet[str]


__all__ = [
    "ClinicalTrial",
    "AssociatedDisorder",
    "AtcCode",
    "DrugbankInteraction",
    "DrugbankDdi",
    "PubchemBioassay",
    "DrugGeneInteraction",
    "CompoundGeneInteraction",
    "GhsCode",
    "PubmedEntry",
    "Code",
    "CodeTypes",
    "CoOccurrenceType",
    "CoOccurrence",
    "Publication",
    "ComputedProperty",
]
