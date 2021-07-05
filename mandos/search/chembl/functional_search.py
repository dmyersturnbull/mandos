from dataclasses import dataclass
from typing import Optional, Sequence, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import MiscUtils
from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.search.chembl._activity_search import _ActivityHit, _ActivitySearch


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

    @property
    def data_source(self) -> str:
        return "ChEMBL :: functional activity"

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
        hit = self._create_hit(
            c_origin=lookup,
            c_matched=compound.inchikey,
            c_id=compound.chid,
            c_name=compound.name,
            predicate="activity:functional",
            statement="has functional activity for",
            object_id=best_target.chembl,
            object_name=best_target.name,
            record_id=from_super.req_as("activity_id", str),
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
