import logging
from dataclasses import dataclass
from typing import Sequence, Set, Optional

from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.model.chembl_support import ChemblCompound
from mandos.model.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.search.chembl._activity_search import _ActivitySearch, _ActivityHit


@dataclass(frozen=True, order=True, repr=True)
class BindingHit(_ActivityHit):
    """
    An "activity" hit for a compound.
    """

    pchembl: float
    std_type: str
    standard_relation: str

    @property
    def predicate(self) -> str:
        return "activity"


class BindingSearch(_ActivitySearch[BindingHit]):
    """
    Search for ``activity`` of type "B".
    """

    @classmethod
    def allowed_assay_types(cls) -> Set[str]:
        return {"B"}

    def to_hit(
        self,
        lookup: str,
        compound: ChemblCompound,
        data: NestedDotDict,
        best_target: ChemblTargetGraph,
    ) -> Sequence[BindingHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        from_super = self._extract(lookup, compound, data)
        hit = BindingHit(
            record_id=from_super.req_as("activity_id", str),
            origin_inchikey=lookup,
            matched_inchikey=compound.inchikey,
            compound_id=compound.chid,
            compound_name=compound.name,
            predicate="binds to",
            object_id=best_target.chembl,
            object_name=best_target.name,
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source,
            exact_target_id=from_super.req_as("target_chembl_id", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
            src_id=from_super.req_as("src_id", str),
            pchembl=from_super.req_as("pchembl_value", float),
            std_type=from_super.req_as("standard_type", str),
            standard_relation=from_super.req_as("standard_relation", str),
        )
        return [hit]


__all__ = ["BindingHit", "BindingSearch"]
