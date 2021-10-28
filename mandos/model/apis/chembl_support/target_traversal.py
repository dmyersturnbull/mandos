from __future__ import annotations

import abc
import enum
import sre_compile
from pathlib import Path
from typing import Dict, Mapping, MutableMapping, Optional, Sequence, Set
from typing import Tuple as Tup
from typing import Type

import decorateme
import regex
from pocketutils.core.exceptions import ParsingError
from pocketutils.tools.reflection_tools import ReflectionTools

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support.chembl_target_graphs import (
    ChemblTargetGraph,
    TargetEdgeReqs,
    TargetNode,
    TargetRelType,
)
from mandos.model.apis.chembl_support.chembl_targets import ChemblTarget, TargetType
from mandos.model.utils.resources import MandosResources


class Acceptance(enum.Enum):
    always = enum.auto()
    never = enum.auto()
    at_start = enum.auto()
    at_end = enum.auto()


@decorateme.auto_repr_str()
class TargetTraversalStrategy(metaclass=abc.ABCMeta):
    """ """

    @classmethod
    def api(cls) -> ChemblApi:
        raise NotImplementedError()

    def traverse(self, target: ChemblTargetGraph) -> Sequence[ChemblTargetGraph]:
        return self.__call__(target)

    def __call__(self, target: ChemblTargetGraph) -> Sequence[ChemblTargetGraph]:
        """
        Run the strategy.
        """
        raise NotImplementedError()


class NullTargetTraversalStrategy(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """ """

    @classmethod
    def api(cls) -> ChemblApi:
        raise NotImplementedError()

    def traverse(self, target: ChemblTargetGraph) -> Sequence[ChemblTargetGraph]:
        return self.__call__(target)

    def __call__(self, target: ChemblTargetGraph) -> Sequence[ChemblTargetGraph]:
        return [target]


class StandardTargetTraversalStrategy(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """ """

    @classmethod
    def edges(cls) -> Set[TargetEdgeReqs]:
        raise NotImplementedError()

    @classmethod
    def acceptance(cls) -> Mapping[TargetEdgeReqs, Acceptance]:
        raise NotImplementedError()

    def __call__(self, target: ChemblTargetGraph) -> Sequence[ChemblTarget]:
        found = target.traverse(self.edges())
        return [f.target for f in found if self.accept(f)]

    def accept(self, target: TargetNode) -> bool:
        if target.link_reqs is None:
            # typically for root nodes -- we'll have a self-loop to check, too
            return False
        acceptance_type = self.acceptance()[target.link_reqs]
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
        pat_type = r"(@?[a-z_]+)"
        pat_rel = r"([<>~=.*])"
        pat_accept = r"(?:accept:([\-*^$]))?"
        pat_src_words = r"(?:src:'''(.+?)''')?"
        pat_dest_words = r"(?:dest:'''(.+?)''')?"
        comment = r"(?:#(.*))?"
        pat = f"^ *{pat_type} *{pat_rel} *{pat_type} *{pat_accept} *{pat_src_words} *{pat_dest_words} *{comment} *$"
        pat = regex.compile(pat, flags=regex.V1)
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
        edge_to_acceptance: MutableMapping[TargetEdgeReqs, Acceptance] = {}
        for line in lines:
            match = pat.fullmatch(line)
            if match is None:
                raise ParsingError(f"Could not parse line '{line}'")
            try:
                sources = TargetType.resolve(match.group(1))
                rel = to_rel[match.group(2)]
                dests = TargetType.resolve(match.group(3))
                accept = to_accept[match.group(4).lower()]
                src_pat = (
                    None
                    if match.group(5) is None or match.group(5) == ""
                    else regex.compile(match.group(5), flags=regex.V1)
                )
                dest_pat = (
                    None
                    if match.group(6) is None or match.group(6) == ""
                    else regex.compile(match.group(6), flags=regex.V1)
                )
            except (KeyError, TypeError, sre_compile.error):
                raise AssertionError(f"Could not parse line '{line}'")
            for source in sources:
                for dest in dests:
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
    def standard_strategies(cls) -> Set[str]:
        return {p.stem for p in MandosResources.dir("strategies").iterdir() if p.suffix == ".strat"}

    @classmethod
    def by_name(cls, name: str, api: ChemblApi) -> TargetTraversalStrategy:
        if name == "@null":  # just slightly more efficient
            return cls.null(api)
        if MandosResources.contains("strategies", name, suffix=".strat"):
            return cls.from_resource(name, api)
        elif name.endswith(".strat"):
            return cls.from_file(Path(name), api)
        return cls.by_classname(name, api)

    @classmethod
    def by_classname(cls, fully_qualified: str, api: ChemblApi) -> TargetTraversalStrategy:
        clazz = ReflectionTools.injection(fully_qualified, TargetTraversalStrategy)
        return cls.create(clazz, api)

    @classmethod
    def from_resource(cls, name: str, api: ChemblApi) -> TargetTraversalStrategy:
        path = MandosResources.file("strategies", name, suffix=".strat")
        return cls.from_file(path, api)

    @classmethod
    def from_file(cls, path: Path, api: ChemblApi) -> TargetTraversalStrategy:
        lines = StandardStrategyParser.read_lines(path)
        return cls._from_lines(lines, api, name="TraversalStrategy" + path.stem.capitalize())

    @classmethod
    def from_lines(
        cls, lines: Sequence[str], api: ChemblApi, *, name: str
    ) -> TargetTraversalStrategy:
        return cls._from_lines(lines, api, name=name)

    @classmethod
    def _from_lines(
        cls, lines: Sequence[str], api: ChemblApi, *, name: str
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

            def __repr__(self) -> str:
                return name + "(" + str(self.api()) + ")"

            def __str__(self) -> str:
                return repr(self)

        Strategy.__name__ = name
        return Strategy()

    @classmethod
    def null(cls, api: ChemblApi) -> TargetTraversalStrategy:
        class NullStrategy(NullTargetTraversalStrategy):
            @classmethod
            def api(cls) -> ChemblApi:
                return api

        return NullStrategy()

    # noinspection PyAbstractClass
    @classmethod
    def create(cls, clz: Type[TargetTraversalStrategy], api: ChemblApi) -> TargetTraversalStrategy:
        class X(clz):
            @classmethod
            def api(cls) -> ChemblApi:
                return api

        X.__name__ = clz.__name__
        return X()


__all__ = ["TargetTraversalStrategy", "TargetTraversalStrategies"]
