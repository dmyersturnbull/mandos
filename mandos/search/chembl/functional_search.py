import enum
import logging
from dataclasses import dataclass
from typing import Sequence, Optional, Set

from mandos.search.chembl._activity_search import _ActivitySearch, _ActivityHit
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_support import ChemblCompound, AssayType
from mandos.model.chembl_support.chembl_target_graphs import ChemblTargetGraph

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True)
class FunctionalHit(_ActivityHit):
    """
    An "activity" hit of type "F" for a compound.
    """

    tissue: Optional[str]
    cell_type: Optional[str]
    subcellular_region: Optional[str]


class FunctionalSearch(_ActivitySearch[FunctionalHit]):
    """
    Search for ``activity`` of type "F".
    """

    @classmethod
    def allowed_assay_types(cls) -> Set[str]:
        return {"F"}

    def to_hit(
        self,
        lookup: str,
        compound: ChemblCompound,
        data: NestedDotDict,
        best_target: ChemblTargetGraph,
    ) -> Sequence[FunctionalHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        from_super = self._extract(lookup, compound, data)
        hit = FunctionalHit(
            record_id=from_super.req_as("activity_id", str),
            origin_inchikey=lookup,
            matched_inchikey=compound.inchikey,
            compound_id=compound.chid,
            compound_name=compound.name,
            predicate="functional activity",
            object_id=best_target.chembl,
            object_name=best_target.name,
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source,
            exact_target_id=from_super.req_as("target_chembl_id", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
            src_id=from_super.req_as("src_id", str),
            tissue=from_super.get_as("tissue", str),
            cell_type=from_super.get_as("cell_type", str),
            subcellular_region=from_super.get("subcellular_region", str),
        )
        return [hit]


__all__ = ["FunctionalHit", "FunctionalSearch"]
