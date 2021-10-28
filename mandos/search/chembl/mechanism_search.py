from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.apis.chembl_support.chembl_targets import TargetFactory
from mandos.model.concrete_hits import MechanismHit
from mandos.model.utils.setup import logger
from mandos.search.chembl._protein_search import ProteinSearch


class MechanismSearch(ProteinSearch[MechanismHit]):
    """
    Search for ``mechanisms``.
    """

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        return list(self.api.mechanism.filter(parent_molecule_chembl_id=parent_form.chid))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> bool:
        if target.type.name.lower() not in {s.lower() for s in self.allowed_target_types}:
            logger.caution(
                f"Excluding {target.name} with type {target.type} ({compound.chid} [{compound.inchi}])"
            )
            logger.debug(f" Excluded {target.name} for {compound} with type {target.type}: {data}")
            return False
        return True

    def to_hit(
        self,
        lookup: str,
        compound: ChemblCompound,
        data: NestedDotDict,
        best_target: ChemblTargetGraph,
    ) -> Sequence[MechanismHit]:
        # ChEMBL recently dropped target_pref_name, so we'll need to find it
        exact_target_obj = self._target_factory.find(data["target_chembl_id"])
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        source = self._format_source()
        predicate = self._format_predicate(action=data.req_as("action_type", str).lower())
        hit = self._create_hit(
            c_origin=lookup,
            c_matched=compound.inchikey,
            c_id=compound.chid,
            c_name=compound.name,
            data_source=source,
            predicate=predicate,
            object_id=best_target.chembl,
            object_name=best_target.name,
            record_id=data["mec_id"],
            exact_target_id=exact_target_obj.chembl,
            exact_target_name=exact_target_obj.name,
            action_type=data.req_as("action_type", str),
            description=data.req_as("mechanism_of_action", str),
        )
        return [hit]


__all__ = ["MechanismSearch"]
