from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Set
from typing import Tuple as Tup

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import ChemblApi

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
    unknown = enum.auto()


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
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
    name: Optional[str]
    type: TargetType

    @classmethod
    def api(cls):
        # TODO use injection and/or TypeVar
        return ChemblApi.wrap(Chembl)

    @classmethod
    def find(cls, chembl: str) -> Target:
        targets = cls.api().target.filter(target_chembl_id=chembl)
        assert len(targets) == 1, f"Found {len(targets)} targets"
        target = NestedDotDict(targets[0])
        return Target(
            id=int(target["target_chembl_id"].replace("CHEMBL", "")),
            name=target.get("pref_name"),
            type=TargetType[target["target_type"].replace(" ", "_").lower()],
        )

    @property
    def chembl(self) -> str:
        """The ChEMBL ID with the 'CHEMBL' prefix."""
        return "CHEMBL" + str(self.id)

    def parents(self) -> Sequence[Target]:
        """
        Gets adjacent targets in the DAG.

        Returns:
        """
        relations = self.__class__.api().target_relation.filter(target_chembl_id=self.chembl)
        links = []
        for superset in [r for r in relations if r["relationship"] == "SUPERSET OF"]:
            linked_target = self.find(superset["related_target_chembl_id"])
            links.append(linked_target)
        return sorted(links)

    def traverse_smart(self) -> Target:
        ok = {
            TargetType.single_protein,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
            TargetType.protein_family,
            TargetType.unknown,
        }
        # TODO depth-first only works if all branches join up within the set `ok`
        found = [
            (i, t)
            for i, t in sorted(self.ancestors(ok), reverse=True)
            if t.type != TargetType.unknown
        ]
        found_preferred = [(i, t) for i, t in found if t.type != TargetType.protein_family]
        if len(found_preferred) > 0:
            return found_preferred[0][1]
        elif len(found) > 0:
            # `len(found_preferred) == 0` implies `self.type not in ok`
            assert self.type not in ok, f"Target {self} is ok but no ok ancestors were found!"
            logger.warning(f"Target {self} has type {self.type}")
            return found[0][1]
        else:
            raise ValueError(f"No matches found for target {self}")

    def ancestors(self, permitting: Set[TargetType]) -> Set[Tup[int, Target]]:
        """
        Traverses the DAG from this node, hopping only to targets with type in the given set.

        Args:
            permitting: The set of target types we're allowed to follow links onto

        Returns:
            The targets in the set, in a breadth-first order (then sorted by CHEMBL ID)
        """
        results = set()
        self._traverse(0, permitting, results)
        return results

    def _traverse(
        self, depth: int, permitting: Set[TargetType], results: Set[Tup[int, Target]]
    ) -> None:
        if self in results or self.type not in permitting:
            return
        for parent in self.parents():
            parent._traverse(depth + 1, permitting, results)
        results.add((depth, self))
