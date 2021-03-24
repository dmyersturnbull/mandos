import abc
import logging
import re
from dataclasses import dataclass
from typing import Sequence, TypeVar, Set, Union

from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import ChemblCompound
from mandos.model.chembl_support.chembl_targets import TargetFactory
from mandos.model.chembl_support.chembl_target_graphs import (
    ChemblTargetGraph,
    ChemblTargetGraphFactory,
)
from mandos.model.chembl_support.chembl_utils import ChemblUtils
from mandos.model.taxonomy import Taxonomy
from mandos.search.chembl import ChemblHit, ChemblSearch
from mandos.search.chembl.target_traversal import TargetTraversalStrategies, TargetTraversalStrategy


@dataclass(frozen=True, order=True, repr=True)
class ProteinHit(ChemblHit, metaclass=abc.ABCMeta):
    """
    A protein target entry for a compound.
    """

    exact_target_id: str


H = TypeVar("H", bound=ProteinHit, covariant=True)


class ProteinSearch(ChemblSearch[H], metaclass=abc.ABCMeta):
    """
    Abstract search.
    """

    def __init__(
        self,
        key: str,
        api: ChemblApi,
        taxa: Sequence[Taxonomy],
        traversal_strategy: str,
        allowed_target_types: Set[str],
    ):
        super().__init__(key, api)
        self.taxa = taxa
        self.traversal_strategy = TargetTraversalStrategies.by_name(traversal_strategy, self.api)
        self.allowed_target_types = allowed_target_types

    def is_in_taxa(self, species: Union[int, str]) -> bool:
        """
        Returns true if the ChEMBL species is contained in any of our taxonomies.
        """
        return any((taxon.contains(species) for taxon in self.taxa))

    def _set_to_regex(self, values) -> str:
        return "(" + "|".join([f"(?:{re.escape(v)})" for v in values]) + ")"

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        raise NotImplementedError()

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> bool:
        """
        Filter based on the returned (activity/mechanism) data.
        IGNORE filters about the target itself, including whether it's a valid target.
        Return True in these cases (better yet, don't check).

        Args:
            lookup:
            compound:
            data:
            target:

        Returns:

        """
        raise NotImplementedError()

    def to_hit(
        self,
        lookup: str,
        compound: ChemblCompound,
        data: NestedDotDict,
        best_target: ChemblTargetGraph,
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
        raise NotImplementedError()

    def find(self, lookup: str) -> Sequence[H]:
        """

        Args:
            lookup:

        Returns:

        """
        form = ChemblUtils(self.api).get_compound(lookup)
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
        if data.get("target_chembl_id") is None:
            logger.debug(f"target_chembl_id missing from mechanism '{data}' for compound {lookup}")
            return []
        chembl_id = data["target_chembl_id"]
        factory = TargetFactory(self.api)
        target_obj = factory.find(chembl_id)
        graph_factory = ChemblTargetGraphFactory.create(self.api, factory)
        graph = graph_factory.at_target(target_obj)
        if not self.should_include(lookup, compound, data, graph):
            return []
        # traverse() will return the source target if it's a non-traversable type (like DNA)
        # and the subclass decided whether to filter those
        # so don't worry about that here
        ancestors = self.traversal_strategy(graph)
        lst = []
        for ancestor in ancestors:
            lst.extend(self.to_hit(lookup, compound, data, ancestor))
        return lst


__all__ = ["ProteinHit", "ProteinSearch"]
