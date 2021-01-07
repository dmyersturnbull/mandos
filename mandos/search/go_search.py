from __future__ import annotations

import abc
import enum
import logging
from dataclasses import dataclass
from typing import Sequence, Type, Union

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, Search
from mandos.search.protein_search import ProteinHit, ProteinSearch

logger = logging.getLogger("mandos")


class GoType(enum.Enum):
    component = enum.auto()
    function = enum.auto()
    process = enum.auto()

    @classmethod
    def of(cls, s: Union[str, GoType]) -> GoType:
        if isinstance(s, GoType):
            return s
        return GoType[s.lower()]


@dataclass(frozen=True, order=True, repr=True)
class GoHit(AbstractHit, metaclass=abc.ABCMeta):
    """
    A mechanism entry for a compound.
    """

    go_type: str
    protein_hit: ProteinHit

    @property
    def predicate(self) -> str:
        return f"has GO {self.go_type} term"


class GoSearch(Search[GoHit], metaclass=abc.ABCMeta):
    """
    Search for GO terms.
    """

    @property
    def go_type(self) -> GoType:
        raise NotImplementedError()

    @property
    def protein_search(self) -> Type[ProteinSearch]:
        raise NotImplementedError()

    def find(self, compound: str) -> Sequence[GoHit]:
        matches = self.protein_search(self.api, self.config, self.tax).find(compound)
        terms = []
        for match in matches:
            target = self.api.target.get(match.object_id)
            terms.extend(self._process(match, target))
        return terms

    def _process(self, match: ProteinHit, target: NestedDotDict) -> Sequence[GoHit]:
        terms = set()
        if target.get("target_components") is not None:
            for comp in target["target_components"]:
                if comp.get("target_component_xrefs") is not None:
                    for xref in comp["target_component_xrefs"]:
                        if xref["xref_src_db"] == f"Go{self.go_type.name.capitalize()}":
                            terms.add((xref["xref_id"], xref["xref_name"]))
        hits = []
        for xref_id, xref_name in terms:
            hits.append(
                GoHit(
                    None,
                    compound_id=match.compound_id,
                    inchikey=match.inchikey,
                    compound_lookup=match.compound_lookup,
                    compound_name=match.compound_name,
                    object_id=xref_id,
                    object_name=xref_name,
                    go_type=self.go_type.name,
                    protein_hit=match,
                )
            )
        return hits


class GoSearchFactory:
    @classmethod
    def create(
        cls, go_type: Union[str, GoType], protein_search: Type[ProteinSearch]
    ) -> Type[GoSearch]:
        go_type = GoType.of(go_type)

        class X(GoSearch):
            @property
            def go_type(self) -> GoType:
                return go_type

            @property
            def protein_search(self) -> Type[ProteinSearch]:
                return protein_search

        X.__name__ = f"Go{go_type.name.capitalize()}From{protein_search.search_name}Search"
        return X


__all__ = ["GoHit", "GoSearch", "GoSearchFactory", "GoType"]
