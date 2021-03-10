import logging
from dataclasses import dataclass
from typing import Sequence, Set, Optional

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import ChemblCompound
from mandos.model.chembl_support.chembl_targets import ChemblTarget
from mandos.model.taxonomy import Taxonomy
from mandos.search.chembl._protein_search import ProteinHit, ProteinSearch
from mandos.search.chembl.target_traversal import (
    TargetTraversalStrategy,
    TargetTraversalStrategies,
)

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True)
class MechanismHit(ProteinHit):
    """
    A mechanism entry for a compound.
    """

    action_type: str
    direct_interaction: bool
    description: str
    exact_target_id: str

    @property
    def predicate(self) -> str:
        return self.action_type.lower()


class MechanismSearch(ProteinSearch[MechanismHit]):
    """
    Search for ``mechanisms``.
    """

    def __init__(
        self,
        chembl_api: ChemblApi,
        tax: Taxonomy,
        traversal_strategy: str,
        allowed_target_types: Set[str],
        min_confidence_score: Optional[int],
    ):
        super().__init__(chembl_api, tax, traversal_strategy)
        self.allowed_target_types = allowed_target_types
        self.min_confidence_score = min_confidence_score

    @property
    def default_traversal_strategy(self) -> TargetTraversalStrategy:
        return TargetTraversalStrategies.strategy0(self.api)

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        return list(self.api.mechanism.filter(parent_molecule_chembl_id=parent_form.chid))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTarget
    ) -> bool:
        if target.type.name.lower() not in {s.lower() for s in self.allowed_target_types}:
            logger.warning(f"Excluding {target} with type {target.type}")
            return False
        return True

    def to_hit(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTarget
    ) -> Sequence[MechanismHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        x = NestedDotDict(
            dict(
                record_id=data["mec_id"],
                compound_id=compound.chid,
                inchikey=compound.inchikey,
                compound_name=compound.name,
                compound_lookup=lookup,
                action_type=data["action_type"],
                direct_interaction=data["direct_interaction"],
                description=data["mechanism_of_action"],
                exact_target_id=data["target_chembl_id"],
            )
        )
        return [MechanismHit(**x, object_id=target.chembl, object_name=target.name)]


__all__ = ["MechanismHit", "MechanismSearch"]
