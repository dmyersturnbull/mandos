import abc
from typing import TypeVar

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_scrape_api import ChemblScrapePage, ChemblScrapeApi
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


class ChemblSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: ChemblApi):
        super().__init__(key)
        self.api = api


__all__ = ["ChemblSearch", "ChemblScrapeSearch", "ChemblScrapePage"]
