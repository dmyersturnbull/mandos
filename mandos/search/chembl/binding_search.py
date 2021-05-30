from dataclasses import dataclass
from typing import Sequence, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support import ChemblTargetGraph
from mandos.search.chembl._activity_search import _ActivitySearch, _ActivityHit


@dataclass(frozen=True, order=True, repr=True)
class BindingHit(_ActivityHit):
    """
    An "activity" hit for a compound.
    """

    pchembl: float
    std_type: str
    standard_relation: str


class BindingSearch(_ActivitySearch[BindingHit]):
    """
    Search for ``activity`` of type "B".
    """

    @property
    def data_source(self) -> str:
        return "ChEMBL :: binding activity"

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
        rel = from_super.req_as("standard_relation", str)
        pchembl = from_super.req_as("pchembl_value", float)
        if (
            self.binds_cutoff is not None
            and pchembl >= self.binds_cutoff
            and rel in {"=", "~", "<", "<="}
        ):
            predicate = f"binds"
        elif (
            self.does_not_bind_cutoff is not None
            and pchembl <= self.does_not_bind_cutoff
            and rel in {"=", "~", ">", ">="}
        ):
            predicate = f"does not bind"
        else:
            predicate = f"binding {rel} at"
        hit = BindingHit(
            record_id=from_super.req_as("activity_id", str),
            origin_inchikey=lookup,
            matched_inchikey=compound.inchikey,
            compound_id=compound.chid,
            compound_name=compound.name,
            predicate=predicate,
            object_id=best_target.chembl,
            object_name=best_target.name,
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source,
            exact_target_id=from_super.req_as("target_chembl_id", str),
            taxon_id=from_super.get("taxon_id"),
            taxon_name=from_super.get("taxon_name"),
            src_id=from_super.req_as("src_id", str),
            pchembl=pchembl,
            std_type=from_super.req_as("standard_type", str),
            standard_relation=rel,
        )
        return [hit]


__all__ = ["BindingHit", "BindingSearch"]
