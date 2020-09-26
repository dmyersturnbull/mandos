import abc
import logging
from dataclasses import dataclass
from typing import Generator, Sequence, TypeVar

from pocketutils.core.dot_dict import NestedDotDict

from mandos.api import ChemblFilterQuery
from mandos.model import AbstractHit, ChemblCompound, Search
from mandos.model.targets import Target, TargetFactory, TargetType

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class ProteinHit(AbstractHit, metaclass=abc.ABCMeta):
    """
    A protein target entry for a compound.
    """


H = TypeVar("H", bound=ProteinHit, covariant=True)


class ProteinSearch(Search[H], metaclass=abc.ABCMeta):
    """
    Abstract search.
    """

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        raise NotImplementedError()

    def should_include(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> bool:
        """
        Filter based on the returned (activity/mechanism) data.
        IGNORE filters about the target itself, including whether it's a valid target.
        Return True in these cases (better yet, don't check).

        Args:
            lookup:
            compound:
            data:

        Returns:

        """
        raise NotImplementedError()

    def to_hit(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, best_target: Target
    ) -> Sequence[H]:
        """
        Gets the desired data as a NestedDotDict from the data from a single element
        returned by ``api_endpoint.filter``.
        This MUST MATCH the constructor, EXCEPT for object_id and object_name,
        which come from traversal and should be added by ``ProteinSearch.to_hit`` (parameter ``best_target``).

        Turns the final data into ``H``.
        Note that this has a default behavior but could be overridden to split into multiple hits
        and/or to add additional attributes that might come from ``best_target``.

        Args:
            lookup:
            compound:
            data:
            best_target:

        Returns:
            A sequence of hits.
        """
        h = self.get_h()
        return [h(**data, object_id=best_target.chembl, object_name=best_target.name)]

    def find(self, lookup: str) -> Sequence[H]:
        """

        Args:
            lookup:

        Returns:

        """
        form = self.get_compound(lookup)
        results = self.query(form)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(lookup, form, result))
        return hits

    def process(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> Sequence[H]:
        """

        Args:
            lookup:
            compound:
            data:

        Returns:

        """
        # CHECK SUBCLASS FILTERS
        # do this first because it's almost definitely fast
        if not self.should_include(lookup, compound, data):
            return []
        if data.get("target_chembl_id") is None:
            logger.debug(f"target_chembl_id missing from mechanism '{data}' for compound {lookup}")
            return []
        chembl_id = data["target_chembl_id"]
        target_obj = TargetFactory.find(chembl_id, self.api)
        if (
            target_obj.type.priority < 0
            or target_obj.type.priority == 0
            and self.config.min_confidence_score < 4
        ):
            logger.warning(f"Excluding {target_obj} with type {target_obj.type}")
            return []
        # traverse() will return the source target if it's a non-traversable type
        # so don't worry about that here
        ancestor = self.traverse(target_obj)
        return self.to_hit(lookup, compound, data, ancestor)

    def traverse(self, target: Target) -> Target:
        """

        Returns:

        """
        if target.type.priority == 0:
            # non-traversable type
            return target
        # priority > 0: traversable type
        traversable_types = {t for t in TargetType if t.priority > 0}
        accepted = target.ancestors(traversable_types)
        # sort by priority, then by depth
        # we want high priority, then high depth (further up the tree)
        # TODO depth-first only works if all branches join up within the set `traversable_types`
        accepted = sorted(
            accepted, key=lambda it: (it[1].type.priority, it[0], it[1]), reverse=True
        )
        # in the worst case, Target.traverse() returns the source target
        return accepted[0][1]


__all__ = ["ProteinHit", "ProteinSearch"]
