import abc
from typing import Sequence, TypeVar

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_scrape_api import ChemblScrapeApi, ChemblScrapePage
from mandos.model.apis.chembl_support.chembl_target_graphs import (
    ChemblTargetGraphFactory,
)
from mandos.model.apis.chembl_support.chembl_targets import TargetFactory
from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


class ChemblScrapeSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: ChemblApi, scrape: ChemblScrapeApi):
        super().__init__(key)
        self.api = api
        self.scrape = scrape

    @classmethod
    def page(cls) -> ChemblScrapePage:
        raise NotImplementedError()

    @classmethod
    def data_source_hierarchy(cls) -> Sequence[str]:
        return ["ChEMBL"]


class ChemblSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: ChemblApi):
        super().__init__(key)
        self.api = api
        self._target_factory = TargetFactory(self.api)
        self._graph_factory = ChemblTargetGraphFactory.create(self.api, self._target_factory)

    @classmethod
    def data_source_hierarchy(cls) -> Sequence[str]:
        return ["ChEMBL"]


__all__ = ["ChemblSearch", "ChemblScrapeSearch", "ChemblScrapePage"]
