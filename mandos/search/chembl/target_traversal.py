from __future__ import annotations
import abc
import enum
import sys
import sre_compile
import re
from pathlib import Path
from typing import Dict, Sequence, Type, Set, Optional, Mapping
from typing import Tuple as Tup

from mandos.model import MandosResources
from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support.chembl_targets import TargetType, ChemblTarget
from mandos.model.chembl_support.chembl_target_graphs import (
    ChemblTargetGraph,
    TargetNode,
    TargetEdgeReqs,
    TargetRelType,
)


class Acceptance(enum.Enum):
    always = enum.auto()
    never = enum.auto()
    at_start = enum.auto()
    at_end = enum.auto()


class TargetTraversalStrategy(metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def api(cls) -> ChemblApi:
        raise NotImplementedError()

    def traverse(self, target: ChemblTargetGraph) -> Sequence[ChemblTargetGraph]:
        return self.__call__(target)

    def __call__(self, target: ChemblTargetGraph) -> Sequence[ChemblTargetGraph]:
        """

        Returns:

        """
        raise NotImplementedError()


class StandardTargetTraversalStrategy(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    @classmethod
    @property
    def edges(cls) -> Set[TargetEdgeReqs]:
        raise NotImplementedError()

    @classmethod
    @property
    def acceptance(cls) -> Mapping[TargetEdgeReqs, Acceptance]:
        raise NotImplementedError()

    def __call__(self, target: ChemblTargetGraph) -> Sequence[ChemblTarget]:
        if not target.type.is_traversable:
            return [target.target]
        found = target.traverse(self.edges)
        return [f.target for f in found if self.accept(f)]

    def accept(self, target: TargetNode) -> bool:
        acceptance_type = self.acceptance[target.link_reqs]
        return (
            acceptance_type is Acceptance.always
            or (acceptance_type is Acceptance.at_start and target.is_start)
            or (acceptance_type is Acceptance.at_end and target.is_end)
        )


class StandardStrategyParser:
    @classmethod
    def read_lines(cls, path: Path) -> Sequence[str]:
        return [
            line
            for line in path.read_text(encoding="utf8").splitlines()
            if not line.startswith("#") and len(line.strip()) > 0
        ]

    @classmethod
    def parse(
        cls, lines: Sequence[str]
    ) -> Tup[Set[TargetEdgeReqs], Mapping[TargetEdgeReqs, Acceptance]]:
        pat_type = r"([a-z_]+)"
        pat_rel = r"([<>~=])"
        pat_accept = r"(?:accept:([\-*^$]?))?"
        pat_src_words = r"(?:src:'''(.+?)''')?"
        pat_dest_words = r"(?:dest:'''(.+?)''')?"
        comment = r"(?:#(.*))?"
        pat = f"^ *{pat_type} *{pat_rel} *{pat_type} *{pat_accept} * {pat_src_words} *{pat_dest_words} *{comment} *$"
        pat = re.compile(pat)
        to_rel = {
            ">": TargetRelType.superset_of,
            "<": TargetRelType.subset_of,
            "~": TargetRelType.overlaps_with,
            "=": TargetRelType.equivalent_to,
            "*": TargetRelType.any_link,
            ".": TargetRelType.self_link,
        }
        to_accept = {
            "*": Acceptance.always,
            "-": Acceptance.never,
            "^": Acceptance.at_start,
            "$": Acceptance.at_end,
        }
        edges = set()
        edge_to_acceptance: Dict[TargetEdgeReqs, Acceptance] = {}
        for line in lines:
            match = pat.fullmatch(line)
            if match is None:
                raise AssertionError(f"Could not parse line '{line}'")
            try:
                src_str = match.group(1).lower()
                sources = TargetType.all_types() if src_str == "any" else [TargetType[src_str]]
                rel = to_rel[match.group(2)]
                dest_str = match.group(3).lower()
                targets = TargetType.all_types() if dest_str == "any" else [TargetType[dest_str]]
                accept = to_accept[match.group(4).lower()]
                src_pat = (
                    None
                    if match.group(5) is None or match.group(5) == ""
                    else re.compile(match.group(5))
                )
                dest_pat = (
                    None
                    if match.group(6) is None or match.group(6) == ""
                    else re.compile(match.group(6))
                )
            except (KeyError, TypeError, sre_compile.error):
                raise AssertionError(f"Could not parse line '{line}'")
            for source in sources:
                for dest in targets:
                    edge = TargetEdgeReqs(
                        src_type=source,
                        src_pattern=src_pat,
                        rel_type=rel,
                        dest_type=dest,
                        dest_pattern=dest_pat,
                    )
                    edges.add(edge)
                    edge_to_acceptance[edge] = accept
        return edges, edge_to_acceptance


class TargetTraversalStrategies:
    """
    Factory.
    """

    @classmethod
    def by_name(cls, fully_qualified: str, api: ChemblApi) -> TargetTraversalStrategy:
        """
        For dependency injection.

        Args:
            fully_qualified:
            api:

        Returns:

        """
        s = fully_qualified
        mod = s[: s.rfind(".")]
        clz = s[s.rfind(".") :]
        x = getattr(sys.modules[mod], clz)
        return cls.create(x, api)

    @classmethod
    def from_resource(cls, name: str, api: ChemblApi) -> TargetTraversalStrategy:
        path = MandosResources.path("strategies", name).with_suffix(".txt")
        lines = StandardStrategyParser.read_lines(path)
        return cls._from_lines(lines, api, path.stem)

    @classmethod
    def from_file(cls, path: Path, api: ChemblApi) -> TargetTraversalStrategy:
        lines = StandardStrategyParser.read_lines(path)
        return cls._from_lines(lines, api, path.stem)

    @classmethod
    def from_lines(
        cls, lines: Sequence[str], api: ChemblApi, name: Optional[str]
    ) -> TargetTraversalStrategy:
        return cls._from_lines(lines, api, "" if name is None else name)

    @classmethod
    def _from_lines(
        cls, lines: Sequence[str], api: ChemblApi, name: str
    ) -> TargetTraversalStrategy:
        edges, accept = StandardStrategyParser.parse(lines)

        class Strategy(StandardTargetTraversalStrategy):
            @classmethod
            def edges(cls) -> Set[TargetEdgeReqs]:
                return edges

            @classmethod
            def acceptance(cls) -> Mapping[TargetEdgeReqs, Acceptance]:
                return accept

            @classmethod
            def api(cls) -> ChemblApi:
                return api

        Strategy.__name__ = StandardTargetTraversalStrategy.__class__.__name__ + "_" + name
        return Strategy()

    @classmethod
    def null(cls, api: ChemblApi) -> TargetTraversalStrategy:
        return cls.from_resource("null.txt", api)

    # noinspection PyAbstractClass
    @classmethod
    def create(cls, clz: Type[TargetTraversalStrategy], api: ChemblApi) -> TargetTraversalStrategy:
        """
        Factory method.

        Args:
            clz:
            api:

        Returns:

        """

        class X(clz):
            @classmethod
            def api(cls) -> ChemblApi:
                return api

        X.__name__ = clz.__name__
        return X()


__all__ = ["TargetTraversalStrategy", "TargetTraversalStrategies"]
