from __future__ import annotations
import logging
import enum
from typing import Optional, Sequence, Set
from dataclasses import dataclass


logger = logging.getLogger(__package__)


class DataFlag(enum.Enum):
    outside = enum.auto()
    transcription = enum.auto()


class TaxLevel(enum.Enum):
    Species = enum.auto()
    Family = enum.auto()


class ObjectKind(enum.Enum):
    Property = enum.auto()
    Biomolecule = enum.auto()
    Indication = enum.auto()
    SideEffect = enum.auto()
    LegalStatus = enum.auto()


@dataclass
class TargetLevel:
    SingleProtein = enum.auto()
    ProteinFamily = enum.auto()
    Receptor = enum.auto()
    ReceptorGroup = enum.auto()


@dataclass
class Compound:
    chembl: int
    name: str
    inchikey: str


@dataclass
class Organism:
    name: str
    is_group: bool
    #parent: Organism
    #children: Set[Organism]


@dataclass
class Component:
    uniprot: str
    description: str


@dataclass
class Target:
    #level: TargetLevel
    chembl: int
    name: str
    classification: Sequence[str]
    organism: Organism
    #parent: Optional[Target]
    #children: Set[Target]


@dataclass
class Predicate:
    name: str


@dataclass
class Activity:
    compound: Compound
    predicate: Predicate
    target: Target
    pchembl: Optional[str]

    def over(self, pchembl: str):
        return float(self.pchembl) >= float(pchembl)
