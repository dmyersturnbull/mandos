import abc
import sys
from typing import Sequence, Type

from mandos.chembl_api import ChemblApi
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


class TargetTraversalStrategy0(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    def __call__(self, target: Target) -> Sequence[Target]:
        """

        Returns:

        """
        return [target]


class TargetTraversalStrategy1(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    def __call__(self, target: Target) -> Sequence[Target]:
        """
        Returns:

        """
        edges = {
            DagTargetLinkType(
                TargetType.selectivity_group,
                TargetRelationshipType.superset_of,
                TargetType.protein_complex_group,
            ),
            DagTargetLinkType(
                TargetType.protein_complex_group,
                TargetRelationshipType.subset_of,
                TargetType.protein_complex_group,
            ),
            DagTargetLinkType(
                TargetType.selectivity_group,
                TargetRelationshipType.superset_of,
                TargetType.protein_family,
            ),
            DagTargetLinkType(
                TargetType.protein_family,
                TargetRelationshipType.subset_of,
                TargetType.protein_family,
            ),
        }
        found = target.traverse(edges)
        return [f.target for f in found if f.is_end]


class TargetTraversalStrategy2(TargetTraversalStrategy, metaclass=abc.ABCMeta):
    """"""

    def __call__(self, target: Target) -> Sequence[Target]:
        """

        Returns:

        """
        # traverse the DAG up and down, following only desired links
        # some links from complex to complex group are "overlaps with"
        # ex: CHEMBL4296059
        # it's also rare to need going from a selectivity group "down" to complex group / family / etc.
        # usually they have a link upwards
        # so...
        # If it's a single protein, it's too risk to traverse up into complexes
        # That's because lots of proteins *occasionally* make complexes, and there are some weird ones
        # BUT We want to catch some obvious cases like GABA A subunits
        # ChEMBL calls many of these "something subunit something"
        # This is the only time we'll allow going directly from protein to complex
        # In this case, we'll also disallow links form protein to family,
        # just because we're pretty sure it's a subunit
        # But we can go from single protein to complex to complex group to family
        if (
            target.type
            in [
                TargetType.single_protein,
                TargetType.protein_family,
                TargetType.protein_complex,
                TargetType.protein_complex_group,
            ]
            and ("subunit" in target.name.split(" ") or "chain" in target.name.split(" "))
        ):
            edges = {
                DagTargetLinkType(
                    TargetType.single_protein,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_complex,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex,
                    TargetRelationshipType.overlaps_with,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex_group,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex_group,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
                DagTargetLinkType(
                    TargetType.protein_family,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
            }
        elif target.type in [TargetType.single_protein, TargetType.protein_family]:
            edges = {
                DagTargetLinkType(
                    TargetType.single_protein,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
                DagTargetLinkType(
                    TargetType.protein_family,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
            }
        elif target.type in [TargetType.protein_complex, TargetType.protein_complex_group]:
            edges = {
                DagTargetLinkType(
                    TargetType.protein_complex,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex,
                    TargetRelationshipType.overlaps_with,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex_group,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex_group,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
                DagTargetLinkType(
                    TargetType.protein_family,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
            }
        elif target.type == TargetType.selectivity_group:
            edges = {
                DagTargetLinkType(
                    TargetType.selectivity_group,
                    TargetRelationshipType.superset_of,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.protein_complex_group,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_complex_group,
                ),
                DagTargetLinkType(
                    TargetType.selectivity_group,
                    TargetRelationshipType.superset_of,
                    TargetType.protein_family,
                ),
                DagTargetLinkType(
                    TargetType.protein_family,
                    TargetRelationshipType.subset_of,
                    TargetType.protein_family,
                ),
            }
        else:
            return [target]
        for edge in set(edges):
            edges.add(
                DagTargetLinkType(
                    edge.source_type, TargetRelationshipType.equivalent_to, edge.dest_type
                )
            )
        found = target.traverse(edges)
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
