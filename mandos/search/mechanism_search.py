import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, ChemblCompound, Search
from mandos.model.targets import TargetFactory, TargetType

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class MechanismHit(AbstractHit):
    """
    A mechanism entry for a compound.
    """

    action_type: str
    direct_interaction: bool
    description: str
    comment: str
    exact_target_id: str

    @property
    def predicate(self) -> str:
        return self.action_type.lower()


class MechanismSearch(Search[MechanismHit]):
    """
    Search for ``mechanisms``.
    """

    def find(self, lookup: str) -> Sequence[MechanismHit]:
        """

        Args:
            lookup:

        Returns:

        """
        form = self.get_compound(lookup)
        results = self.api.mechanism.filter(parent_molecule_chembl_id=form.chid)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(lookup, form, result))
        return hits

    def process(
        self, lookup: str, compound: ChemblCompound, mechanism: NestedDotDict
    ) -> Sequence[MechanismHit]:
        """

        Args:
            lookup:
            compound:
            mechanism:

        Returns:

        """
        data = dict(
            record_id=mechanism["mec_id"],
            compound_id=compound.chid,
            inchikey=compound.inchikey,
            compound_name=compound.name,
            compound_lookup=lookup,
            action_type=mechanism["action_type"],
            direct_interaction=mechanism["direct_interaction"],
            description=mechanism["mechanism_of_action"],
            comment=mechanism["mechanism_comment"],
            exact_target_id=mechanism["target_chembl_id"],
        )
        target_obj = TargetFactory.find(mechanism["target_chembl_id"], self.api)
        if target_obj.type == TargetType.unknown:
            logger.error(f"Target {target_obj} has type UNKNOWN")
            return []
        ancestor = target_obj.traverse_smart()
        return [MechanismHit(**data, object_id=ancestor.chembl, object_name=ancestor.name)]


__all__ = ["MechanismHit", "MechanismSearch"]
