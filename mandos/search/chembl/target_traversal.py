from __future__ import annotations
import abc
import sys
import re
from pathlib import Path
from typing import Sequence, Type, Set

from mandos.model import MandosResources
from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support.chembl_targets import (
    DagTargetLinkType,
    ChemblTarget,
    TargetRelationshipType,
    TargetType,
)


class TargetTraversalStrategy(metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def api(cls) -> ChemblApi:
        raise NotImplementedError()

    def traverse(self, target: ChemblTarget) -> Sequence[ChemblTarget]:
        return self.__call__(target)

    def __call__(self, target: ChemblTarget) -> Sequence[ChemblTarget]:
        """

        Returns:

        """
        raise NotImplementedError()


class StandardTargetTraversalStrategy(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def edges(cls) -> Set[DagTargetLinkType]:
        raise NotImplementedError()

    @classmethod
    def read(cls, path: Path) -> Set[DagTargetLinkType]:
        lines = [
            line
            for line in path.read_text(encoding="utf8").splitlines()
            if not line.startswith("#") and len(line.strip()) > 0
        ]
        return cls.parse(lines)

    @classmethod
    def parse(cls, lines: Sequence[str]) -> Set[DagTargetLinkType]:
        pat_type = re.compile(r"([a-z_]+)")
        pat_rel = re.compile(r"((?:->)|(?:<-)|(?:==)|(?:~~))")
        pat_words = re.compile(r"(?:words: *([^|]+(?:\|[^|]+)+))?")
        pat = re.compile(f"^ *{pat_type} *{pat_rel} *{pat_type} *{pat_words} *$")
        to_rel = {
            "->": TargetRelationshipType.superset_of,
            "<-": TargetRelationshipType.subset_of,
            "~~": TargetRelationshipType.overlaps_with,
            "==": TargetRelationshipType.equivalent_to,
        }
        edges = set()
        for line in lines:
            match = pat.fullmatch(line)
            if match is None:
                raise AssertionError(f"Could not parse line '{line}'")
            try:
                source = TargetType[match.group(1).lower()]
                rel = TargetRelationshipType[to_rel[match.group(2).lower()]]
                target = TargetType[match.group(3).lower()]
                words = None if match.group(4) == "" else match.group(4).split("|")
            except KeyError:
                raise AssertionError(f"Could not parse line '{line}'")
            edges.add(DagTargetLinkType(source, rel, target, words))
        return edges

    def __call__(self, target: ChemblTarget) -> Sequence[ChemblTarget]:
        """
        Returns:
        """
        if not target.type.is_traversable:
            return [target]
        found = target.traverse(self.edges)
        return [f.target for f in found if f.is_end]


class TargetTraversalStrategy0(StandardTargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def edges(cls) -> Set[DagTargetLinkType]:
        return cls.read(MandosResources.path("strategies", "strategy0.txt"))


class TargetTraversalStrategy1(StandardTargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def edges(cls) -> Set[DagTargetLinkType]:
        return cls.read(MandosResources.path("strategies", "strategy1.txt"))


class TargetTraversalStrategy2(StandardTargetTraversalStrategy, metaclass=abc.ABCMeta):
    """
    Traverse the DAG up and down, following only desired links
    Some links from complex to complex group are "overlaps with"
    ex: CHEMBL4296059
    it's also rare to need going from a selectivity group "down" to complex group / family / etc.
    usually they have a link upwards
    so...
    If it's a single protein, it's too risk to traverse up into complexes
    That's because lots of proteins *occasionally* make complexes, and there are some weird ones
    BUT We want to catch some obvious cases like GABA A subunits
    ChEMBL calls many of these "something subunit something"
    This is the only time we'll allow going directly from protein to complex
    In this case, we'll also disallow links form protein to family,
    just because we're pretty sure it's a subunit
    But we can go from single protein to complex to complex group to family
    """

    @classmethod
    def edges(cls) -> Set[DagTargetLinkType]:
        return cls.read(MandosResources.path("strategies", "strategy2.txt"))


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
    def strategy0(cls, api: ChemblApi) -> TargetTraversalStrategy:
        return cls.create(TargetTraversalStrategy0, api)

    @classmethod
    def strategy1(cls, api: ChemblApi) -> TargetTraversalStrategy:
        return cls.create(TargetTraversalStrategy1, api)

    @classmethod
    def strategy2(cls, api: ChemblApi) -> TargetTraversalStrategy:
        return cls.create(TargetTraversalStrategy2, api)

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
