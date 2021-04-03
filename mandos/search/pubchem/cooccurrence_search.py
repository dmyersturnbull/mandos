import abc
from dataclasses import dataclass
from typing import Sequence, TypeVar

from mandos.model.pubchem_api import PubchemApi
from mandos.model.pubchem_support.pubchem_data import PubchemData
from mandos.model.pubchem_support.pubchem_models import CoOccurrenceType
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class CoOccurrenceHit(PubchemHit, metaclass=abc.ABCMeta):
    score: int
    intersect_count: int
    query_count: int
    neighbor_count: int


@dataclass(frozen=True, order=True, repr=True)
class DiseaseCoOccurrenceHit(CoOccurrenceHit):
    """"""


@dataclass(frozen=True, order=True, repr=True)
class GeneCoOccurrenceHit(CoOccurrenceHit):
    """"""


@dataclass(frozen=True, order=True, repr=True)
class ChemicalCoOccurrenceHit(CoOccurrenceHit):
    """"""


H = TypeVar("H", bound=CoOccurrenceHit, covariant=True)


class CoOccurrenceSearch(PubchemSearch[H], metaclass=abc.ABCMeta):
    """"""

    def __init__(self, key: str, api: PubchemApi, min_score: int, min_articles: int):
        super().__init__(key, api)
        self.min_score = min_score
        self.min_articles = min_articles

    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        raise NotImplementedError()

    @property
    def data_source(self) -> str:
        return "PubChem"

    def _predicate(self) -> str:
        raise NotImplementedError()

    def _query(self, data: PubchemData):
        raise NotImplementedError()

    def find(self, inchikey: str) -> Sequence[H]:
        data = self.api.fetch_data(inchikey)
        allofthem = self._query(data)
        return [
            self.__class__.get_h()(
                record_id=None,
                compound_id=str(data.cid),
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_name=data.name,
                predicate=self._predicate(),
                object_id=dd.neighbor_id,
                object_name=dd.neighbor_name,
                score=dd.score,
                intersect_count=dd.article_count,
                query_count=dd.query_article_count,
                neighbor_count=dd.neighbor_article_count,
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
            )
            for dd in allofthem
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

    def _predicate(self) -> str:
        return "co-occurs with gene"

    def _query(self, data: PubchemData):
        return data.literature.gene_cooccurrences


class ChemicalCoOccurrenceSearch(CoOccurrenceSearch[ChemicalCoOccurrenceHit]):
    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        return CoOccurrenceType.chemical

    def _predicate(self) -> str:
        return "co-occurs with chemical"

    def _query(self, data: PubchemData):
        return data.literature.chemical_cooccurrences


class DiseaseCoOccurrenceSearch(CoOccurrenceSearch[DiseaseCoOccurrenceHit]):
    @classmethod
    def cooccurrence_type(cls) -> CoOccurrenceType:
        return CoOccurrenceType.disease

    def _predicate(self) -> str:
        return "co-occurs with disease"

    def _query(self, data: PubchemData):
        return data.literature.disease_cooccurrences


__all__ = [
    "GeneCoOccurrenceHit",
    "GeneCoOccurrenceSearch",
    "ChemicalCoOccurrenceSearch",
    "ChemicalCoOccurrenceHit",
    "DiseaseCoOccurrenceSearch",
    "DiseaseCoOccurrenceHit",
    "CoOccurrenceSearch",
]
