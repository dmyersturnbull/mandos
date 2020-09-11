from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Sequence, Set

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger(__package__)


class TargetType(enum.Enum):
    """
    Enum corresponding to the ChEMBL API field ``target.target_type``.
    """

    single_protein = enum.auto()
    protein_family = enum.auto()
    protein_complex = enum.auto()
    protein_complex_group = enum.auto()
    selectivity_group = enum.auto()


@dataclass(frozen=True, order=True)
class Target:
    """
    A target from ChEMBL, from the ``target`` table.
    ChEMBL targets form a DAG via the ``target_relation`` table using links of type "SUPERSET OF" and "SUBSET OF".
    (There are additional link types ("OVERLAPS WITH", for ex), which we are ignoring.)
    For some receptors the DAG happens to be a tree. This is not true in general. See the GABAA receptor, for example.
    To fetch a target, use the ``find`` factory method.

    Attributes:
        id: The CHEMBL ID without the 'CHEMBL' prefix; use ``chembl`` to get the string value (with the prefix)
        name: The preferred name (``pref_target_name``)
        type: From the ``target_type`` ChEMBL field
    """

    id: int
    name: str
    type: TargetType

    @classmethod
    def find(cls, chembl: str) -> Target:
        targets = Chembl.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
        target = NestedDotDict(targets[0])
        return Target(
            id=int(target["target_chembl_id"].replace("CHEMBL", "")),
            name=target["pref_target_name"],
            type=TargetType[target["target_type"].replace(" ", "_")],
        )

    @property
    def chembl(self) -> str:
        """The ChEMBL ID with the 'CHEMBL' prefix."""
        return "CHEMBL" + str(self.id)

    def links(self) -> Sequence[Target]:
        """
        Gets adjacent targets in the DAG.

        Returns:
        """
        relations = Chembl.target_relation.filter(target_chembl_id=self.chembl)
        links = []
        for superset in [r for r in relations if r["relationship"] in ["SUPERSET OF", "SUBSET OF"]]:
            linked_target = self.find(superset["related_target_chembl_id"])
            links.append(linked_target)
        return sorted(links)

    def traverse_smart(self) -> Set[Target]:
        ok = {
            TargetType.single_protein,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
        }
        return self.traverse(ok)

    def traverse(self, permitting: Set[TargetType]) -> Set[Target]:
        """
        Traverses the DAG from this node, hopping only to targets with type in the given set.

        Args:
            permitting: The set of target types we're allowed to follow links onto

        Returns:
            The targets in the set, in a breadth-first order (then sorted by CHEMBL ID)
        """
        results = set()
        self._traverse(permitting, results)
        return results

    def _traverse(self, permitting: Set[TargetType], results: Set[Target]) -> Set[Target]:
        results.add(self)
        for link in sorted(self.links()):
            results.add(link)
        for linked in self._traverse(permitting, results):
            if linked.type in permitting:
                results.add(linked)
        return results
