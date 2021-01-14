from __future__ import annotations
import abc
from dataclasses import dataclass
from typing import Union, Type, FrozenSet, Mapping

from pocketutils.core.dot_dict import NestedDotDict

from mandos import MandosResources
from mandos.model import Search


@dataclass(frozen=True, eq=True, repr=True)
class Source(metaclass=abc.ABCMeta):
    meta_ref: str
    ref: str
    name: str
    params: Mapping[str, Union[None, str, int, float]]
    target: Type[Search]


@dataclass(frozen=True, eq=True, repr=True)
class KnowledgeSet:
    sources: FrozenSet[Source]

    @classmethod
    def create(cls, param_values: Mapping[str, Union[None, str, int, float]]) -> KnowledgeSet:
        _data = NestedDotDict.read_json(MandosResources.path("knowledge.json"))
        knowledge = []
        params = {v["key"]: v for v in _data["params"]}
        for source in _data["sources"]:
            for pkey, pvalue in params.items():
                pass
