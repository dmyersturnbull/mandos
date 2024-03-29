import abc
from typing import Optional, Sequence, Set, TypeVar

import regex
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.apis.chembl_support.chembl_utils import ChemblUtils
from mandos.model.apis.chembl_support.target_traversal import TargetTraversalStrategies
from mandos.model.concrete_hits import ProteinHit
from mandos.model.taxonomy_caches import LazyTaxonomy
from mandos.model.utils.setup import logger
from mandos.search.chembl import ChemblSearch

H = TypeVar("H", bound=ProteinHit, covariant=True)


class ProteinSearch(ChemblSearch[H], metaclass=abc.ABCMeta):
    """
    Abstract search.
    """

    def __init__(
        self,
        key: str,
        api: ChemblApi,
        taxa: Optional[LazyTaxonomy],
        traversal: str,
        allowed_target_types: Set[str],
        min_confidence_score: Optional[int],
    ):
        super().__init__(key, api)
        self.taxa = taxa
        self.traversal = TargetTraversalStrategies.by_name(traversal, self.api)
        self.allowed_target_types = allowed_target_types
        self.min_confidence_score = min_confidence_score

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
        _ = self.taxa.get  # do first for better logging
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
            logger.debug(f"target_chembl_id missing from '{data}' for compound {lookup}")
            return []
        graph = self._graph_factory.at_chembl_id(data["target_chembl_id"])
        if not self.should_include(lookup, compound, data, graph):
            return []
        # traverse() will return the source target if it's a non-traversable type (like DNA)
        # and the subclass decided whether to filter those
        # so don't worry about that here
        ancestors = self.traversal(graph)
        lst = []
        for ancestor in ancestors:
            lst.extend(self.to_hit(lookup, compound, data, ancestor))
        return lst

    def _set_to_regex(self, values) -> str:
        return "(" + "|".join([f"(?:{regex.escape(v)})" for v in values]) + ")"


__all__ = ["ProteinSearch"]
