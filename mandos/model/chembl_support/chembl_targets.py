"""
Model of ChEMBL targets and a hierarchy between them as a directed acyclic graph (DAG).
"""
from __future__ import annotations

import abc
import enum
import logging
import re
from dataclasses import dataclass
from typing import Optional, Sequence, Set
from typing import Tuple as Tup

from urllib3.util.retry import MaxRetryError
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_api import ChemblApi

logger = logging.getLogger(__package__)


class TargetNotFoundError(ValueError):
    """"""


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
    protein_nucleic_acid_complex = enum.auto()
    metal = enum.auto()
    small_molecule = enum.auto()
    subcellular = enum.auto()
    unknown = enum.auto()

    @classmethod
    def of(cls, s: str) -> TargetType:
        key = s.replace(" ", "_").replace("-", "_").lower()
        try:
            return TargetType[key]
        except KeyError:
            logger.error(f"Target type {key} not found. Using TargetType.unknown.")
            return TargetType.unknown

    @classmethod
    def protein_types(cls) -> Set[TargetType]:
        return {s for s in cls if s.is_protein}

    @classmethod
    def all_types(cls) -> Set[TargetType]:
        return set(TargetType)  # here for symmetry

    @property
    def is_traversable(self) -> bool:
        return self in {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
            TargetType.selectivity_group,
        }

    @property
    def is_protein(self) -> bool:
        return self in {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
        }

    @property
    def is_unknown(self) -> bool:
        return self == TargetType.unknown


class TargetRelationshipType(enum.Enum):
    subset_of = enum.auto()
    superset_of = enum.auto()
    overlaps_with = enum.auto()
    equivalent_to = enum.auto()

    @classmethod
    def of(cls, s: str) -> TargetRelationshipType:
        return TargetRelationshipType[s.replace(" ", "_").replace("-", "_").lower()]


@dataclass(frozen=True, order=True, repr=True)
class DagTargetLinkType:
    source_type: TargetType
    rel_type: TargetRelationshipType
    dest_type: TargetType
    words: Optional[Set[str]]

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
                    st.add(DagTargetLinkType(source, rel, dest, None))
        return st

    def matches(
        self,
        source: TargetType,
        rel: TargetRelationshipType,
        target: TargetType,
        target_name: Optional[str],
    ) -> bool:
        if self.words is None:
            words_match = True
        else:
            words_match = False
            for choice in self.words:
                if any((word == choice for word in re.compile(r"[ \-_]+").split(target_name))):
                    words_match = True
                    break
        return (
            self.source_type == source
            and self.rel_type == rel
            and self.dest_type == target
            and words_match
        )


@dataclass(frozen=True, order=True, repr=True)
class DagTarget:
    depth: int
    is_end: bool
    target: ChemblTarget
    link_type: Optional[DagTargetLinkType]


@dataclass(frozen=True, order=True, repr=True)
class ChemblTarget(metaclass=abc.ABCMeta):
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
    def find(cls, chembl: str) -> ChemblTarget:
        """

        Args:
            chembl:

        Returns:

        """
        try:
            targets = cls.api().target.filter(target_chembl_id=chembl)
        except MaxRetryError:
            raise TargetNotFoundError(f"Failed to find target {chembl}")
        assert len(targets) == 1, f"Found {len(targets)} targets for {chembl}"
        target = NestedDotDict(targets[0])
        return cls(
            chembl=target["target_chembl_id"],
            name=target.get("pref_name"),
            type=TargetType.of(target["target_type"]),
        )

    def links(
        self, rel_types: Set[TargetRelationshipType]
    ) -> Sequence[Tup[ChemblTarget, TargetRelationshipType]]:
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
        # recursive method called from traverse
        # this got really complex
        # basically, we just want to:
        # for each link (relationship) to another target:
        # for every allowed link type (DagTargetLinkType), try:
        # if the link type is acceptable, add the found target and associated link type, and break
        # all good if we've already traversed this
        if source.target.chembl in {s.target.chembl for s in results}:
            return
        # find all links from ChEMBL, then filter to only the valid links
        # do not traverse yet -- we just want to find these links
        link_candidates = source.target.links({q.rel_type for q in permitting})
        links = []
        for linked_target, rel_type in link_candidates:
            # try out all of the link types that could match
            # getting to the link_target by way of any of them is fine
            # although the DagTarget takes the link_type, we'll just go ahead and break if we find one acceptable link
            # the links are already sorted, so that should be fine
            # (otherwise, we just end up with redundant targets)
            for permitted in permitting:
                if permitted.matches(
                    source.target.type, rel_type, linked_target.type, linked_target.name
                ):
                    link_type = DagTargetLinkType(
                        source.target.type, rel_type, linked_target.type, permitted.words
                    )
                    # purposely use the invalid value None for is_root
                    linked = DagTarget(source.depth + 1, None, linked_target, link_type)
                    links.append(linked)
                    break
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
    def find(cls, chembl: str, api: ChemblApi) -> ChemblTarget:
        """

        Args:
            chembl:
            api:

        Returns:
            A ``Target`` instance from a newly created subclass of that class
        """

        @dataclass(frozen=True, order=True, repr=True)
        class _Target(ChemblTarget):
            @classmethod
            def api(cls) -> ChemblApi:
                return api

        _Target.__name__ = "Target:" + chembl
        return _Target.find(chembl)


__all__ = [
    "TargetType",
    "TargetRelationshipType",
    "ChemblTarget",
    "DagTarget",
    "TargetFactory",
    "DagTargetLinkType",
    "TargetNotFoundError",
]
