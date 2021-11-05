from __future__ import annotations

import abc
import enum
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional, Sequence, Set
from typing import Tuple as Tup
from typing import Type

import decorateme
import regex
from pocketutils.core.enums import CleverEnum
from pocketutils.core.exceptions import XTypeError

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support.chembl_targets import (
    ChemblTarget,
    TargetFactory,
    TargetType,
)
from mandos.model.utils.setup import logger


@dataclass(frozen=True, order=True, repr=True)
class TargetNode:
    """
    A target with information about how we reached it from a traversal.

    Attributes:
        depth: The number of steps taken to get here, with 0 for the root
        is_end: If there was no edge to follow from here (that we hadn't already visited)
        target: Our target
        link_reqs: The set of requirements for the link that we matched to get here
        origin: The parent of our target node
    """

    depth: int
    is_end: bool
    target: ChemblTarget
    link_reqs: Optional[TargetEdgeReqs]
    origin: Optional[TargetNode]

    @property
    def is_start(self) -> bool:
        return self.depth == 0


@decorateme.auto_obj()
class AbstractTargetEdgeReqs(metaclass=abc.ABCMeta):
    """
    A set of requirements for a (source, rel, dest) triple.
    This determines the edges we're allowed to follow in the graph.
    """

    def matches(
        self,
        src: TargetNode,
        rel_type: TargetRelType,
        dest: TargetNode,
    ) -> bool:
        raise NotImplementedError()


@dataclass(frozen=True, order=True, repr=True)
class TargetEdgeReqs(AbstractTargetEdgeReqs):
    """
    A set of requirements for a (source, rel, dest) triple.
    This determines the edges we're allowed to follow in the graph.
    """

    src_type: TargetType
    src_pattern: Optional[regex.Pattern]
    rel_type: TargetRelType
    dest_type: TargetType
    dest_pattern: Optional[regex.Pattern]

    @classmethod
    def cross(
        cls,
        source_types: Set[TargetType],
        rel_types: Set[TargetRelType],
        dest_types: Set[TargetType],
    ) -> Set[TargetEdgeReqs]:
        """
        Returns a "cross-product" over the three types.
        Note that none will contain text patterns.

        Args:
            source_types:
            rel_types:
            dest_types:
        """
        st = set()
        for source in source_types:
            for rel in rel_types:
                for dest in dest_types:
                    st.add(
                        TargetEdgeReqs(
                            src_type=source,
                            src_pattern=None,
                            rel_type=rel,
                            dest_type=dest,
                            dest_pattern=None,
                        )
                    )
        return st

    def matches(
        self,
        src: TargetNode,
        rel_type: TargetRelType,
        dest: TargetNode,
    ) -> bool:
        """
        Determines whether a (source, rel, dest) triple matches this set of requirements.

        Args:
            src:
            rel_type:
            dest:
        """
        srcx = src.target
        destx = dest.target
        return (
            (
                self.src_pattern is None
                or (srcx.name is not None and self.src_pattern.fullmatch(srcx.name))
            )
            and (
                self.dest_pattern is None
                or (destx.name is not None and self.dest_pattern.fullmatch(destx.name))
            )
            and self.src_type == srcx.type
            and self.rel_type == rel_type
            and self.dest_type == destx.type
        )


class TargetRelType(CleverEnum):
    """
    A relationship between two targets.

    Types:
        - subset_of, superset_of, overlaps_with, and equivalent_to are actual types in ChEMBL.
        - any_link means any of the ChEMBL-defined types
        - self_link is an implicit link from any target to itself
    """

    subset_of = enum.auto()
    superset_of = enum.auto()
    overlaps_with = enum.auto()
    equivalent_to = enum.auto()
    any_link = enum.auto()
    self_link = enum.auto()

    @classmethod
    def of(cls, s: str) -> TargetRelType:
        return TargetRelType[s.replace(" ", "_").replace("-", "_").lower()]


@total_ordering
class ChemblTargetGraph(metaclass=abc.ABCMeta):
    # noinspection PyUnresolvedReferences
    """
    A target from ChEMBL, from the ``target`` table.
    ChEMBL targets form a DAG via the ``target_relation`` table using links of type "SUPERSET OF" and "SUBSET OF".
    (There are additional link types ("OVERLAPS WITH", for ex), which we are ignoring.)
    For some receptors the DAG happens to be a tree. This is not true in general. See the GABAA receptor, for example.
    To fetch a target, use the ``find`` factory method.
    """

    def __init__(self, node: TargetNode):
        if not isinstance(node, TargetNode):
            raise XTypeError(f"Bad type {type(node)} for {node}")
        self.node = node

    def __repr__(self):
        return f"{self.__class__.__name__}({self.node})"

    def __str__(self):
        return f"{self.__class__.__name__}({self.node})"

    def __hash__(self):
        return hash(self.node)

    def __eq__(self, target):
        if not isinstance(target, ChemblTargetGraph):
            raise XTypeError(f"Bad type {type(target)} for {target}")
        return self.node == target.node

    def __lt__(self, target):
        if not isinstance(target, ChemblTargetGraph):
            raise XTypeError(f"Bad type {type(target)} for {target}")
        return self.node.__lt__(target.node)

    @classmethod
    def at_chembl_id(cls, chembl_id: str) -> ChemblTargetGraph:
        target = cls.factory().find(chembl_id)
        # noinspection PyTypeChecker
        return cls(TargetNode(0, None, target, None, None))

    @classmethod
    def at_node(cls, target: TargetNode) -> ChemblTargetGraph:
        if not isinstance(target, TargetNode):
            raise XTypeError(f"Bad type {type(target)} for {target}")
        return cls(target)

    @classmethod
    def at_target(cls, target: ChemblTarget) -> ChemblTargetGraph:
        # lie and fill in None -- we don't know because we haven't traversed
        if not isinstance(target, ChemblTarget):
            raise XTypeError(f"Bad type {type(target)} for {target}")
        # noinspection PyTypeChecker
        return cls(TargetNode(0, None, target, None, None))

    @classmethod
    def api(cls) -> ChemblApi:
        raise NotImplementedError()

    @classmethod
    def factory(cls) -> TargetFactory:
        raise NotImplementedError()

    @property
    def target(self) -> ChemblTarget:
        return self.node.target

    @property
    def chembl(self) -> str:
        return self.target.chembl

    @property
    def name(self) -> Optional[str]:
        return self.target.name

    @property
    def type(self) -> TargetType:
        return self.target.type

    def links(
        self, rel_types: Set[TargetRelType]
    ) -> Sequence[Tup[ChemblTargetGraph, TargetRelType]]:
        """
        Gets adjacent targets in the graph.

        Args:
            rel_types: Relationship types (e.g. "superset of") to include
                       If ``TargetRelType.self_link`` is included, will add a single self-link
        """
        api = self.__class__.api()
        relations = api.target_relation.filter(target_chembl_id=self.target.chembl)
        links = []
        # "subset" means "up" (it's reversed from what's on the website)
        for superset in relations:
            linked_id = superset["related_target_chembl_id"]
            rel_type = TargetRelType.of(superset["relationship"])
            if rel_type in rel_types or TargetRelType.any_link in rel_types:
                linked_target = self.__class__.at_target(self.factory().find(linked_id))
                links.append((linked_target, rel_type))
        # we need to add self-links separately
        if TargetRelType.self_link in rel_types:
            links.append(
                (self.at_target(self.factory().find(self.target.chembl)), TargetRelType.self_link)
            )
        return sorted(links)

    def traverse(self, permitting: Set[TargetEdgeReqs]) -> Set[TargetNode]:
        """
        Traverses the DAG from this node, hopping only to targets with type in the given set.

        Args:
            permitting: The set of target types we're allowed to follow links onto

        Returns:
            The targets in the set, in a breadth-first order (then sorted by CHEMBL ID)
            The int is the depth, starting at 0 (this protein), going to +inf for the highest ancestors
        """
        results: Set[TargetNode] = set()
        logger.debug(
            f"Starting traversal from {self.target} (permitting: {', '.join([str(s) for s in permitting])}"
        )
        # purposely use the invalid value None for is_root
        # noinspection PyTypeChecker
        self._traverse(TargetNode(0, None, self, None, None), permitting, results)
        if any((x.is_end is None for x in results)):
            raise AssertionError()
        logger.debug(f"Got {len(results)} from traversal on {self.target}")
        return results

    @classmethod
    def _traverse(
        cls, source: TargetNode, permitting: Set[TargetEdgeReqs], results: Set[TargetNode]
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
        logger.trace(
            f"Traversing from {source.target.chembl} ({', '.join([str(s) for s in permitting])}"
        )
        # find all links from ChEMBL, then filter to only the valid links
        # do not traverse yet -- we just want to find these links
        link_candidates = cls.at_node(source).links({q.rel_type for q in permitting})
        links = []
        for linked_target, rel_type in link_candidates:
            # try out all of the link types that could match
            # record ALL of the ones that matched, even for duplicate targets
            # that's because the caller might care about the edge type that matched, not just the dest target
            # The caller might also care about the src target
            for permitted in permitting:
                if permitted.matches(
                    src=source,
                    rel_type=rel_type,
                    dest=linked_target.node,
                ):
                    link_type = TargetEdgeReqs(
                        src_type=source.target.type,
                        src_pattern=permitted.src_pattern,
                        rel_type=rel_type,
                        dest_type=linked_target.type,
                        dest_pattern=permitted.dest_pattern,
                    )
                    # purposely use the invalid value None for is_root
                    # noinspection PyTypeChecker
                    linked = TargetNode(source.depth + 1, None, linked_target, link_type, source)
                    links.append(linked)
                    # now add a self-link
                    # don't worry -- we'll make sure not to traverse it
        # now, we'll add our own (breadth-first, remember)
        # we know whether we're at an "end" node by whether we found any links
        # note that this is an invariant of the node (and permitted link types): it doesn't depend on traversal order
        is_at_end = len(links) == 0
        # this is BASICALLY the same as ``results.add(source)``:
        # the only difference is we NOW know whether we're at the end (there's nowhere to go from there)
        # (we had no idea before checking all of its children)
        # source.origin is the parent DagTarget OF source; it's None *iff* this is the root (``self`` in ``traverse``)
        final_origin_target = TargetNode(
            source.depth, is_at_end, source.target, source.link_reqs, source.origin
        )
        results.add(final_origin_target)
        # alright! now traverse on the links
        for link in links:
            # this check is needed
            # otherwise we can go superset --- subset --- superset ---
            # or just --- overlaps with --- overlaps with ---
            # obviously also don't traverse self-links
            if link not in results and link.link_reqs.rel_type is not TargetRelType.self_link:
                cls._traverse(link, permitting, results)
        # we've added: ``source``, and then each of its children (with recursion)
        # we're done now


@decorateme.auto_utils()
class ChemblTargetGraphFactory:
    def __init__(self, graph_type: Type[ChemblTargetGraph]):
        self.graph_type = graph_type

    @classmethod
    def create(cls, api: ChemblApi, target_factory: TargetFactory) -> ChemblTargetGraphFactory:
        class CreatedChemblTargetGraph(ChemblTargetGraph):
            @classmethod
            def api(cls) -> ChemblApi:
                return api

            @classmethod
            def factory(cls) -> TargetFactory:
                return target_factory

        return ChemblTargetGraphFactory(CreatedChemblTargetGraph)

    def at_chembl_id(self, chembl_id: str) -> ChemblTargetGraph:
        return self.graph_type.at_chembl_id(chembl_id)

    def at_node(self, target: TargetNode) -> ChemblTargetGraph:
        return self.graph_type.at_node(target)

    def at_target(self, target: ChemblTarget) -> ChemblTargetGraph:
        # lie and fill in None -- we don't know because we haven't traversed
        # noinspection PyTypeChecker
        return self.graph_type.at_target(target)


__all__ = [
    "ChemblTargetGraph",
    "ChemblTargetGraphFactory",
    "TargetEdgeReqs",
    "TargetNode",
    "TargetRelType",
]
