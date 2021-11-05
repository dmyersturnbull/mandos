import abc
from typing import Sequence, TypeVar

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.pubchem_support.pubchem_models import CoOccurrenceType
from mandos.model.concrete_hits import (
    ChemicalCoOccurrenceHit,
    CoOccurrenceHit,
    DiseaseCoOccurrenceHit,
    GeneCoOccurrenceHit,
)
from mandos.search.pubchem import PubchemSearch

H = TypeVar("H", bound=CoOccurrenceHit, covariant=True)


class CoOccurrenceSearch(PubchemSearch[H], metaclass=abc.ABCMeta):
    """ """

    def __init__(self, key: str, api: PubchemApi, min_score: int, min_articles: int):
        super().__init__(key, api)
        self.min_score = min_score
        self.min_articles = min_articles

    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        raise NotImplementedError()

    def _source(self) -> str:
        return self._format_source()

    def _predicate(self) -> str:
        return self._format_predicate()

    def _query(self, data: PubchemData):
        raise NotImplementedError()

    def find(self, inchikey: str) -> Sequence[H]:
        data = self.api.fetch_data(inchikey)
        all_of_them = self._query(data)
        return [
            self._create_hit(
                c_origin=inchikey,
                c_id=str(data.cid),
                c_matched=data.names_and_identifiers.inchikey,
                c_name=data.name,
                data_source=self._source(),
                predicate=self._predicate(),
                object_id=dd.neighbor_id,
                object_name=dd.neighbor_name,
                weight=dd.score,
                intersect_count=dd.article_count,
                query_count=dd.query_article_count,
                neighbor_count=dd.neighbor_article_count,
                cache_date=data.names_and_identifiers.modify_date,
            )
            for dd in all_of_them
            if (
                dd.score >= self.min_score
                and dd.neighbor_article_count >= self.min_articles
                and dd.query_article_count >= self.min_articles
            )
        ]


class GeneCoOccurrenceSearch(CoOccurrenceSearch[GeneCoOccurrenceHit]):
    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        return CoOccurrenceType.gene

    def _query(self, data: PubchemData):
        return data.literature.gene_cooccurrences


class ChemicalCoOccurrenceSearch(CoOccurrenceSearch[ChemicalCoOccurrenceHit]):
    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        return CoOccurrenceType.chemical

    def _query(self, data: PubchemData):
        return data.literature.chemical_cooccurrences


class DiseaseCoOccurrenceSearch(CoOccurrenceSearch[DiseaseCoOccurrenceHit]):
    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        return CoOccurrenceType.disease

    def _query(self, data: PubchemData):
        return data.literature.disease_cooccurrences


__all__ = [
    "ChemicalCoOccurrenceSearch",
    "CoOccurrenceSearch",
    "DiseaseCoOccurrenceSearch",
    "GeneCoOccurrenceSearch",
]
