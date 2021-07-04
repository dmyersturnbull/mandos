from dataclasses import dataclass
from typing import Sequence

from mandos.model import MiscUtils
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class AcuteEffectHit(PubchemHit):
    """ """

    organism: str
    human: bool
    test_type: str
    route: str
    effect: str
    mg_per_kg: float


@dataclass(frozen=True, order=True, repr=True)
class Ld50Hit(PubchemHit):
    """ """

    organism: str
    human: bool


class AcuteEffectSearch(PubchemSearch[AcuteEffectHit]):
    """ """

    def __init__(self, key: str, api: PubchemApi, top_level: bool):
        super().__init__(key, api)
        self.top_level = top_level

    @property
    def data_source(self) -> str:
        return "ChemIDplus :: acute effects"

    def find(self, inchikey: str) -> Sequence[AcuteEffectHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.toxicity.acute_effects:
            for effect in dd.effects:
                effect_name = effect.category.lower() if self.top_level else effect.lower()
                results.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        predicate="effect",
                        statement="causes effect",
                        object_id=effect_name,
                        object_name=effect_name,
                        effect=effect.lower(),
                        organism=dd.organism,
                        human=dd.organism.is_human,
                        route=dd.route,
                        mg_per_kg=dd.mg_per_kg,
                        test_type=dd.test_type,
                    )
                )
        return results


class Ld50Search(PubchemSearch[Ld50Hit]):
    @property
    def data_source(self) -> str:
        return "ChemIDplus"

    def find(self, inchikey: str) -> Sequence[Ld50Hit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.toxicity.acute_effects:
            if dd.test_type != "LD50":
                continue
            results.append(
                self._create_hit(
                    Ld50Hit,
                    inchikey=inchikey,
                    data=data,
                    predicate="has LD50",
                    object_id=str(dd.mg_per_kg),
                    object_name=str(dd.mg_per_kg),
                    organism=dd.organism,
                    human=dd.organism.is_human,
                )
            )
        return results


__all__ = ["AcuteEffectHit", "AcuteEffectSearch", "Ld50Hit", "Ld50Search"]
