from typing import Sequence, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.concrete_hits import FunctionalHit
from mandos.search.chembl._activity_search import _ActivitySearch


class FunctionalSearch(_ActivitySearch[FunctionalHit]):
    """
    Search for ``activity`` of type "F".
    """

    @classmethod
    def assay_type(cls) -> str:
        return "F"

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
        source = self._format_source(
            src_id=from_super.req_as("src_id", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
            tissue=from_super.get_as("cell_type", str, ""),
            subcellular_region=from_super.get("subcellular_region", str),
        )
        predicate = self._format_predicate(
            tissue=from_super.get_as("cell_type", str, ""),
            cell_type=from_super.get_as("cell_type", str),
            subcellular_region=from_super.get("subcellular_region", str),
        )
        hit = self._create_hit(
            c_origin=lookup,
            c_matched=compound.inchikey,
            c_id=compound.chid,
            c_name=compound.name,
            data_source=source,
            predicate=predicate,
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


__all__ = ["FunctionalSearch"]
