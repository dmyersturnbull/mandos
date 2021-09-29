from __future__ import annotations

from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.concrete_hits import BindingHit, GoHit, GoType
from mandos.search.chembl import ChemblSearch
from mandos.search.chembl.binding_search import BindingSearch


class GoSearch(ChemblSearch[GoHit]):
    """
    Search for GO terms.
    """

    def __init__(self, key: str, api: ChemblApi, go_type: GoType, binding_search: BindingSearch):
        super().__init__(key, api)
        self.go_type = go_type
        self.binding_search = binding_search

    def find(self, compound: str) -> Sequence[GoHit]:
        matches = self.binding_search.find(compound)
        terms = []
        for match in matches:
            target = self.api.target.get(match.object_id)
            terms.extend(self._process(compound, match, target))
        return terms

    def _process(self, lookup: str, compound: BindingHit, target: NestedDotDict) -> Sequence[GoHit]:
        terms = set()
        if target.get("target_components") is not None:
            for comp in target["target_components"]:
                if comp.get("target_component_xrefs") is not None:
                    for xref in comp["target_component_xrefs"]:
                        if xref["xref_src_db"] == f"Go{self.go_type.name.capitalize()}":
                            terms.add((xref["xref_id"], xref["xref_name"]))
        hits = []
        for xref_id, xref_name in terms:
            source = self._format_source(type=self.go_type.name)
            predicate = self._format_predicate(type=self.go_type.name)
            hits.append(
                self._create_hit(
                    c_origin=lookup,
                    c_matched=compound.matched_inchikey,
                    c_id=compound.compound_id,
                    c_name=compound.compound_name,
                    data_source=source,
                    predicate=predicate,
                    object_id=xref_id,
                    object_name=xref_name,
                    go_type=self.go_type.name,
                    binding=compound,
                )
            )
        return hits


__all__ = ["GoSearch"]
