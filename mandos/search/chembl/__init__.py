import abc
from typing import TypeVar

from typeddfs import TypedDfs

from mandos.model.settings import QUERY_EXECUTORS

from mandos.model.scrape import Scraper, By
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


class _ScraperSingleton:
    x = None

    @classmethod
    def get(cls):
        if cls.x is None:
            cls.x = Scraper.create(QUERY_EXECUTORS.chembl)
        return cls.x


ChemblTable = TypedDfs.typed("ChemblTable").build()


class ChemblScrapeSearch(Search[H], metaclass=abc.ABCMeta):
    """"""

    @classmethod
    def _page_name(cls) -> str:
        raise NotImplementedError()

    def _scrape(self, chembl_id: int) -> ChemblTable:
        # e.g. target_predictions
        url = f"https://www.ebi.ac.uk/chembl/embed/#compound_report_card/{chembl_id}/{self._page_name}"
        scraper = _ScraperSingleton.get()
        scraper.go(url)
        rows = []
        i = 2
        while True:
            table = scraper.find_element("table", By.TAG_NAME)
            for tr in table.find_elements("tr"):
                rows += [td.text for td in tr.find_elements("td")]
            # noinspection PyBroadException
            try:
                scraper.find_elements(str(i), By.LINK_TEXT)
            except Exception:
                break
            i += 1
        header = rows[0]
        rows = rows[1:]
        return ChemblTable(rows, columns=header)


class ChemblSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: ChemblApi):
        """
        Constructor.

        Args:
            api:
        """
        super().__init__(key)
        self.api = api


__all__ = ["ChemblSearch", "ChemblScrapeSearch", "ChemblTable"]
