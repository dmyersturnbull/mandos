import abc
import sys
from typing import Sequence, Type

from mandos.api import ChemblApi
from mandos.model.targets import DagTargetLinkType, Target, TargetRelationshipType, TargetType


class TargetTraversalStrategy(metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def api(cls) -> ChemblApi:
        raise NotImplementedError()

    def traverse(self, target: Target) -> Sequence[Target]:
        return self.__call__(target)

    def __call__(self, target: Target) -> Sequence[Target]:
        """

        Returns:

        """
        raise NotImplementedError()


class TargetTraversalStrategy1(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    def __call__(self, target: Target) -> Sequence[Target]:
        """

        Returns:

        """
        # traverse the DAG up and down, following only desired links
        # these are:
        # 1. All links from protein-like to protein-like supersets (protein, family, complex, & complex group)
        # 2. Links from complex to complex group "overlaps"
        # 3. From selectivity groups to their subsets
        # Note that this means we could go from selectivity group to single protein, then up to receptor group
        # (But I've never seen that)
        # some links from complex to complex group are "overlaps with"
        # ex: CHEMBL4296059
        permitting = {
            *DagTargetLinkType.cross(
                set(TargetType), {TargetRelationshipType.subset_of}, TargetType.protein_types()
            ),
            *DagTargetLinkType.cross(
                {TargetType.selectivity_group},
                {TargetRelationshipType.subset_of},
                TargetType.protein_types(),
            ),
            DagTargetLinkType(
                TargetType.protein_complex,
                TargetRelationshipType.overlaps_with,
                TargetType.protein_complex_group,
            ),
        }
        found = target.traverse(permitting)
        return [f.target for f in found if f.is_end]


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
    def strategy1(cls, api: ChemblApi) -> TargetTraversalStrategy:
        return cls.create(TargetTraversalStrategy1, api)

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

        X.__name__ = clz.__name__ + "X"
        return X()


__all__ = ["TargetTraversalStrategy", "TargetTraversalStrategy1", "TargetTraversalStrategies"]
