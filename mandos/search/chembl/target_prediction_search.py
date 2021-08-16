from __future__ import annotations

from typing import Sequence, Optional, Tuple, Set

import numpy as np

from mandos.model.apis.chembl_support.chembl_target_graphs import (
    ChemblTargetGraphFactory,
    ChemblTargetGraph,
)
from mandos.model.apis.chembl_support.chembl_targets import TargetFactory
from pocketutils.tools.string_tools import StringTools

from mandos import logger
from mandos.model.taxonomy import Taxonomy, Taxon
from typeddfs import TypedDf

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_scrape_api import (
    ChemblScrapePage,
    ChemblScrapeApi,
    ChemblTargetPredictionTable,
)
from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_utils import ChemblUtils
from mandos.search.chembl import ChemblScrapeSearch
from mandos.model.concrete_hits import ChemblTargetPredictionHit
from mandos.search.chembl.target_traversal import TargetTraversalStrategies

P = ChemblScrapePage.target_predictions
T = ChemblTargetPredictionTable


class TargetPredictionSearch(ChemblScrapeSearch[ChemblTargetPredictionHit]):
    """ """

    @classmethod
    def page(cls) -> ChemblScrapePage:
        return ChemblScrapePage.target_predictions

    def __init__(
        self,
        key: str,
        api: ChemblApi,
        scrape: ChemblScrapeApi,
        taxa: Sequence[Taxonomy],
        traversal: str,
        target_types: Set[str],
        required_level: int = 70,
        min_threshold: float = 1.0,
        binding_score: float = 1.0,
        nonbinding_score: float = 1.0,
    ):
        super().__init__(key, api, scrape)
        self.taxa = taxa
        self.traversal_strategy = TargetTraversalStrategies.by_name(traversal, self.api)
        self.target_types = target_types
        if required_level not in [70, 80, 90]:
            raise ValueError(f"required_level must be 70, 80, or 90, not {required_level}")
        if min_threshold <= 0:
            raise ValueError(f"min_threshold must be positive, not {min_threshold}")
        if binding_score <= 0:
            raise ValueError(f"binding_score must be positive, not {binding_score}")
        if nonbinding_score <= 0:
            raise ValueError(f"nonbinding_score must be positive, not {nonbinding_score}")
        self.required_level = required_level
        self.min_threshold = min_threshold
        self.binding_score = binding_score
        self.nonbinding_score = nonbinding_score

    @property
    def data_source(self) -> str:
        return "ChEMBL :: target predictions"

    def find(self, lookup: str) -> Sequence[ChemblTargetPredictionHit]:
        ch = ChemblUtils(self.api).get_compound_dot_dict(lookup)
        compound = ChemblUtils(self.api).compound_dot_dict_to_obj(ch)
        table: TypedDf = self.scrape.fetch_predictions(compound.chid)
        hits = []
        for row in table.itertuples():
            hits.extend(self.process(lookup, compound, row))
        return hits

    def process(
        self, lookup: str, compound: ChemblCompound, row
    ) -> Sequence[ChemblTargetPredictionHit]:
        tax_id, tax_name = self._get_taxon(row.target_organism)
        if tax_id is tax_name is None:
            return []
        thresh = row.activity_threshold
        if row.activity_threshold < self.min_threshold:
            return []
        factory = TargetFactory(self.api)
        target_obj = factory.find(row.target_chembl_id)
        graph_factory = ChemblTargetGraphFactory.create(self.api, factory)
        graph = graph_factory.at_target(target_obj)
        ancestors: Sequence[ChemblTargetGraph] = self.traversal_strategy(graph)
        lst = []
        for ancestor in ancestors:
            for conf_t, conf_v in zip(
                [70, 80, 90], [row.confidence_70, row.confidence_80, row.confidence_90]
            ):
                predicate = f"binding:{conf_v.yes_no_mixed}"
                weight = (
                    np.sqrt(thresh)
                    * abs(conf_t / (100 - conf_t) * conf_v.score)
                    / 4
                    / np.sqrt(self.min_threshold)
                )
                hit = self._create_hit(
                    c_origin=lookup,
                    c_matched=compound.inchikey,
                    c_id=compound.chid,
                    c_name=compound.name,
                    predicate=predicate,
                    object_id=ancestor.chembl,
                    object_name=ancestor.name,
                    data_source=self.data_source,
                    exact_target_id=row.target_chembl_id,
                    exact_target_name=row.target_pref_name,
                    weight=weight,
                    prediction=conf_v,
                    confidence_set=conf_t,
                    threshold=thresh,
                )
                lst.append(hit)
        return lst

    def _get_taxon(self, organism: str) -> Tuple[Optional[int], Optional[str]]:
        if len(self.taxa) == 0:  # allow all
            return None, organism
        matches = {}
        for tax in self.taxa:
            matches += tax.get_by_id_or_name(organism)
        if len(matches) == 0:
            logger.debug(f"Taxon {organism} not in set. Excluding.")
            return None, None
        best: Taxon = next(iter(matches))
        if best.scientific_name != organism and best.mnemonic != organism:
            logger.warning(f"Organism {organism} matched to {best.scientific_name} by common name")
        if len(matches) > 1:
            logger.warning(
                f"Multiple matches for taxon {organism}: {matches}; using {best.scientific_name}"
            )
        return best.id, organism


__all__ = ["TargetPredictionSearch"]
