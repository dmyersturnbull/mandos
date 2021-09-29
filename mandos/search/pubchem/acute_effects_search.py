from typing import Sequence

import numpy as np

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.concrete_hits import AcuteEffectHit, Ld50Hit
from mandos.search.pubchem import PubchemSearch


class AcuteEffectSearch(PubchemSearch[AcuteEffectHit]):
    """ """

    def __init__(self, key: str, api: PubchemApi, top_level: bool):
        super().__init__(key, api)
        self.top_level = top_level

    def find(self, inchikey: str) -> Sequence[AcuteEffectHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.toxicity.acute_effects:
            for effect in dd.effects:
                effect_name = effect.category.lower() if self.top_level else effect.lower()
                weight = -np.log10(dd.mg_per_kg)
                source = self._format_source(
                    organism=dd.organism,
                    human=dd.organism.is_human,
                    route=dd.route,
                    test_type=dd.test_type,
                )
                predicate = self._format_predicate(
                    organism=dd.organism,
                    human=dd.organism.is_human,
                    route=dd.route,
                    test_type=dd.test_type,
                )
                results.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        data_source=source,
                        predicate=predicate,
                        object_id=effect_name,
                        object_name=effect_name,
                        effect=effect.lower(),
                        organism=dd.organism,
                        human=dd.organism.is_human,
                        route=dd.route,
                        mg_per_kg=dd.mg_per_kg,
                        test_type=dd.test_type,
                        weight=weight,
                    )
                )
        return results


class Ld50Search(PubchemSearch[Ld50Hit]):
    def find(self, inchikey: str) -> Sequence[Ld50Hit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.toxicity.acute_effects:
            if dd.test_type != "LD50":
                continue
            weight = -np.log10(dd.mg_per_kg)
            results.append(
                self._create_hit(
                    inchikey=inchikey,
                    c_id=str(data.cid),
                    c_origin=inchikey,
                    c_matched=data.names_and_identifiers.inchikey,
                    c_name=data.name,
                    data_source="ChemIDplus",
                    predicate="has LD50",
                    object_id=str(dd.mg_per_kg),
                    object_name=str(dd.mg_per_kg),
                    weight=weight,
                    organism=dd.organism,
                    human=dd.organism.is_human,
                    route=dd.route,
                )
            )
        return results


__all__ = ["AcuteEffectSearch", "Ld50Search"]
