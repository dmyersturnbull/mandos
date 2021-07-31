from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.search.chembl._protein_search import ProteinSearch
from mandos.model.concrete_hits import MechanismHit


class MechanismSearch(ProteinSearch[MechanismHit]):
    """
    Search for ``mechanisms``.
    """

    @property
    def data_source(self) -> str:
        return "ChEMBL :: mechanisms"

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        return list(self.api.mechanism.filter(parent_molecule_chembl_id=parent_form.chid))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> bool:
        if target.type.name.lower() not in {s.lower() for s in self.allowed_target_types}:
            logger.warning(f"Excluding {target.name} with type {target.type}")
            return False
        return True

    def to_hit(
        self,
        lookup: str,
        compound: ChemblCompound,
        data: NestedDotDict,
        best_target: ChemblTargetGraph,
    ) -> Sequence[MechanismHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        predicate = "moa:" + data.req_as("action_type", str).lower()
        hit = self._create_hit(
            c_origin=lookup,
            c_matched=compound.inchikey,
            c_id=compound.chid,
            c_name=compound.name,
            predicate=predicate,
            object_id=best_target.chembl,
            object_name=best_target.name,
            record_id=data["mec_id"],
            exact_target_id=data.req_as("target_chembl_id", str),
            action_type=data.req_as("action_type", str),
        )
        return [hit]


__all__ = ["MechanismSearch"]
