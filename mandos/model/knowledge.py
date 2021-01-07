from __future__ import annotations
import abc
from dataclasses import dataclass
from typing import Any, Type, FrozenSet, Mapping


@dataclass(frozen=True, eq=True, repr=True)
class Knowledge(metaclass=abc.ABCMeta):
    meta_ref: str
    ref: str
    name: str
    params: Mapping[str, Type[Any]]
    target: str


def _chembl(name: str, target: str, **params) -> Knowledge:
    return Knowledge(
        meta_ref="ChEMBL",
        ref="ChEMBL",
    )


chembl_moa = _chembl(
    "MoA",
)


@dataclass(frozen=True, eq=True, repr=True)
class KnowledgeSet:
    types: FrozenSet[Knowledge]
