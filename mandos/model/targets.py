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
    nucleic_acid = enum.auto()
    chimeric_protein = enum.auto()
    unknown = enum.auto()

    @classmethod
    def of(cls, s: str) -> TargetType:
        return TargetType[s.replace(" ", "_").replace("-", "_").lower()]

    @classmethod
    def protein_types(cls) -> Set[TargetType]:
        return {s for s in cls if s.is_protein}

    @property
    def is_protein(self) -> bool:
        return self in {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
        }

    @property
    def is_trash(self) -> bool:
        return self == TargetType.unknown

    @property
    def is_strange(self) -> bool:
        return self in {
            TargetType.selectivity_group,
            TargetType.protein_protein_interaction,
            TargetType.nucleic_acid,
            TargetType.chimeric_protein,
            TargetType.unknown,
        }


class TargetRelationshipType(enum.Enum):
    subset_of = enum.auto()
    superset_of = enum.auto()
    overlaps_with = enum.auto()

    @classmethod
    def of(cls, s: str) -> TargetRelationshipType:
        return TargetRelationshipType[s.replace(" ", "_").replace("-", "_").lower()]


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class DagTargetLinkType:
    source_type: TargetType
    rel_type: TargetRelationshipType
    dest_type: TargetType

    @classmethod
    def cross(
        cls,
        source_types: Set[TargetType],
        rel_types: Set[TargetRelationshipType],
        dest_types: Set[TargetType],
    ) -> Set[DagTargetLinkType]:
        st = set()
        for source in source_types:
            for rel in rel_types:
                for dest in dest_types:
                    st.add(DagTargetLinkType(source, rel, dest))
        return st


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class DagTarget:
    depth: int
    is_end: bool
    target: Target
    link_type: Optional[DagTargetLinkType]


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
    def find(cls, chembl: str) -> Target:
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
            type=TargetType.of(target["target_type"]),
        )

    def links(
        self, rel_types: Set[TargetRelationshipType]
    ) -> Sequence[Tup[Target, TargetRelationshipType]]:
        """
        Gets adjacent targets in the DAG.

        Args:
            rel_types:

        Returns:
        """
        relations = self.__class__.api().target_relation.filter(target_chembl_id=self.chembl)
        links = []
        # "subset" means "up" (it's reversed from what's on the website)
        for superset in relations:
            linked_id = superset["related_target_chembl_id"]
            rel_type = TargetRelationshipType.of(superset["relationship"])
            if rel_type in rel_types:
                linked_target = self.find(linked_id)
                links.append((linked_target, rel_type))
        return sorted(links)

    def traverse(self, permitting: Set[DagTargetLinkType]) -> Set[DagTarget]:
        """
        Traverses the DAG from this node, hopping only to targets with type in the given set.

        Args:
            permitting: The set of target types we're allowed to follow links onto

        Returns:
            The targets in the set, in a breadth-first order (then sorted by CHEMBL ID)
            The int is the depth, starting at 0 (this protein), going to +inf for the highest ancestors
        """
        results = set()
        # purposely use the invalid value None for is_root
        self._traverse(DagTarget(0, None, self, None), permitting, results)
        assert not any((x.is_end is None for x in results))
        return results

    @classmethod
    def _traverse(
        cls, source: DagTarget, permitting: Set[DagTargetLinkType], results: Set[DagTarget]
    ) -> None:
        # all good if we've already traversed this
        if source.target.chembl in {s.target.chembl for s in results}:
            return
        # find all links from ChEMBL, then filter to only the valid links
        # do not traverse yet -- we just want to find these links
        link_candidates = source.target.links({q.rel_type for q in permitting})
        links = []
        for link, rel_type in link_candidates:
            link_type = DagTargetLinkType(source.target.type, rel_type, link.type)
            if link_type in permitting:
                # purposely use the invalid value None for is_root
                linked = DagTarget(source.depth + 1, None, link, link_type)
                links.append(linked)
        # now, we'll add our own (breadth-first, remember)
        # we know whether we're at an "end" node by whether we found any links
        # note that this is an invariant of the node (and permitted link types): it doesn't depend on traversal order
        is_at_end = len(links) == 0
        results.add(DagTarget(source.depth, is_at_end, source.target, source.link_type))
        # alright! now traverse on the links
        for link in links:
            # this check is needed
            # otherwise we can go superset --- subset --- superset ---
            # or just --- overlaps with --- overlaps with ---
            if link not in results:
                cls._traverse(link, permitting, results)


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


__all__ = [
    "TargetType",
    "TargetRelationshipType",
    "Target",
    "DagTarget",
    "TargetFactory",
    "DagTargetLinkType",
]
