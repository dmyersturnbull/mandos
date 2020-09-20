"""
Model of ChEMBL targets and a hierarchy between them as a directed acyclic graph (DAG).
"""
from __future__ import annotations

import abc
import enum
import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Set
from typing import Tuple as Tup

from pocketutils.core.dot_dict import NestedDotDict

from mandos.api import ChemblApi

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
    protein_protein_interaction = enum.auto()
    unknown = enum.auto()

    @property
    def priority(self) -> int:
        """
        Higher is better.

        Returns:

        """
        return {
            TargetType.selectivity_group: 0,
            TargetType.protein_protein_interaction: 0,
            TargetType.unknown: 0,
            TargetType.protein_family: 1,
            TargetType.single_protein: 2,
            TargetType.protein_complex: 3,
            TargetType.protein_complex_group: 4,
        }[self]


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class Target(metaclass=abc.ABCMeta):
    """
    A target from ChEMBL, from the ``target`` table.
    ChEMBL targets form a DAG via the ``target_relation`` table using links of type "SUPERSET OF" and "SUBSET OF".
    (There are additional link types ("OVERLAPS WITH", for ex), which we are ignoring.)
    For some receptors the DAG happens to be a tree. This is not true in general. See the GABAA receptor, for example.
    To fetch a target, use the ``find`` factory method.

    Attributes:
        chembl: The CHEMBL ID, starting with 'CHEMBL'
        name: The preferred name (``pref_target_name``)
        type: From the ``target_type`` ChEMBL field
    """

    chembl: str
    name: Optional[str]
    type: TargetType

    @classmethod
    def api(cls) -> ChemblApi:
        """

        Returns:

        """
        raise NotImplementedError()

    @classmethod
    def find(cls, chembl: str) -> __qualname__:
        """

        Args:
            chembl:

        Returns:

        """
        targets = cls.api().target.filter(target_chembl_id=chembl)
        assert len(targets) == 1, f"Found {len(targets)} targets for {chembl}"
        target = NestedDotDict(targets[0])
        return cls(
            chembl=target["target_chembl_id"],
            name=target.get("pref_name"),
            type=TargetType[target["target_type"].replace(" ", "_").lower()],
        )

    @property
    def id(self) -> int:
        """

        Returns:

        """
        return int(self.chembl.replace("CHEMBL", ""))

    def parents(self) -> Sequence[__qualname__]:
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

    def traverse_smart(self) -> __qualname__:
        """

        Returns:

        """
        traversable_types = {
            TargetType.single_protein,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
            TargetType.protein_family,
            TargetType.unknown,
        }
        acceptable_types = {
            TargetType.single_protein,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
            TargetType.protein_family,
        }
        # TODO depth-first only works if all branches join up within the set `traversable_types`
        accepted = [
            (i, t) for i, t in self.ancestors(traversable_types) if t.type in acceptable_types
        ]
        accepted = sorted(
            accepted, key=lambda it: (it[1].type.priority, it[0], it[1]), reverse=True
        )
        if len(accepted) > 0:
            return accepted[0][1]
        else:
            raise ValueError(f"No matches found for target {self}")

    def ancestors(self, permitting: Set[TargetType]) -> Set[Tup[int, __qualname__]]:
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
        self, depth: int, permitting: Set[TargetType], results: Set[Tup[int, __qualname__]]
    ) -> None:
        if self in results or self.type not in permitting:
            return
        for parent in self.parents():
            parent._traverse(depth + 1, permitting, results)
        results.add((depth, self))


class TargetFactory:
    """
    Factory for ``Target`` that injects a ``ChemblApi``.
    """

    @classmethod
    def find(cls, chembl: str, api: ChemblApi) -> Target:
        """

        Args:
            chembl:
            api:

        Returns:
            A ``Target`` instance from a newly created subclass of that class
        """

        @dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
        class _Target(Target):
            @classmethod
            def api(cls) -> ChemblApi:
                return api

        _Target.__name__ = "Target:" + chembl
        return _Target.find(chembl)


__all__ = ["TargetType", "Target", "TargetFactory"]
