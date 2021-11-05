from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.concrete_hits import BindingHit
from mandos.search.chembl._activity_search import _ActivitySearch


class BindingSearch(_ActivitySearch[BindingHit]):
    """
    Search for ``activity`` of type "B".
    """

    @classmethod
    def assay_type(cls) -> str:
        return "B"

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
        rel = from_super.req_as("standard_relation", str)
        pchembl = from_super.req_as("pchembl_value", float)
        truth = self._truth(pchembl, rel)
        source = self._format_source(
            src_id=from_super.req_as("src_id", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
        )
        predicate = self._format_predicate(
            src_id=from_super.req_as("src_id", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
            truth=truth,
            rel=rel,
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
            exact_target_name=from_super.req_as("target_pref_name", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
            src_id=from_super.req_as("src_id", str),
            pchembl=pchembl,
            std_type=from_super.req_as("standard_type", str),
            std_rel=rel,
        )
        return [hit]

    def _truth(self, pchembl: float, rel: str) -> str:
        if (
            self.binds_cutoff is not None
            and pchembl >= self.binds_cutoff
            and rel in {"=", "~", "<", "<="}
        ):
            return "yes"
        return rel


__all__ = ["BindingSearch"]
