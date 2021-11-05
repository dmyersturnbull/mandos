"""
API that web-scrapes ChEMBL.
"""
from __future__ import annotations

import abc
import enum
from functools import cached_property
from pathlib import Path
from typing import Optional, Type

import pandas as pd
from pocketutils.core.enums import CleverEnum
from pocketutils.core.query_utils import QueryExecutor
from typeddfs import TypedDf, TypedDfs

from mandos.model import Api
from mandos.model.settings import QUERY_EXECUTORS, SETTINGS
from mandos.model.utils.setup import logger


class SarPredictionResult(CleverEnum):
    active = enum.auto()
    inactive = enum.auto()
    empty = enum.auto()
    both = enum.auto()

    @property
    def yes_no_mixed(self) -> str:
        return {
            SarPredictionResult.active: "yes",
            SarPredictionResult.inactive: "no",
            SarPredictionResult.empty: "mixed",
            SarPredictionResult.both: "mixed",
        }[self]

    @property
    def score(self) -> int:
        return {
            SarPredictionResult.active: 1,
            SarPredictionResult.inactive: -1,
            SarPredictionResult.empty: 0,
            SarPredictionResult.both: 0,
        }[self]


class ChemblScrapeTable(TypedDf, metaclass=abc.ABCMeta):
    """"""


def _parse_conf(df: pd.DataFrame):
    df = df.copy()
    for t in [70, 80, 90]:
        df[f"confidence_{t}"] = df[f"confidence_{t}"].map(SarPredictionResult.of)


ChemblTargetPredictionTable = (
    TypedDfs.typed("ChemblTargetPredictionTable")
    .subclass(ChemblScrapeTable)
    .require("target_chembl_id", "target_pref_name", "target_organism", dtype=str)
    .require("confidence_70", "confidence_80", "confidence_90", dtype=SarPredictionResult)
    .require("activity_threshold", dtype=float)
    .post(_parse_conf)
    .strict()
    .secure()
    .hash(directory=True)
).build()


class ChemblScrapePage(CleverEnum):
    target_predictions = enum.auto()


class ChemblScrapeApi(Api, metaclass=abc.ABCMeta):
    def fetch_predictions(self, cid: str) -> ChemblTargetPredictionTable:
        return self._fetch_page(
            cid, ChemblScrapePage.target_predictions, ChemblTargetPredictionTable
        )

    def _fetch_page(self, cid: str, page: ChemblScrapePage, table_type: Type[ChemblScrapeTable]):
        raise NotImplementedError()


class QueryingChemblScrapeApi(ChemblScrapeApi):
    def __init__(self, executor: QueryExecutor = QUERY_EXECUTORS.chembl):
        self._executor = executor

    @property
    def scraper(self):
        return self.Scraper.create(self._executor)

    @cached_property
    def By(self):
        from mandos.model.utils.scrape import By

        return By

    @cached_property
    def Scraper(self):
        from mandos.model.utils.scrape import Scraper

        return Scraper

    def _fetch_page(
        self, chembl_id: str, page: ChemblScrapePage, table_type: Type[ChemblScrapeTable]
    ):
        url = f"https://www.ebi.ac.uk/chembl/embed/#compound_report_card/{chembl_id}/{page}"
        scraper = self.scraper
        scraper.go(url)
        rows = []
        i = 2
        while True:
            table = scraper.find_element("table", self.By.TAG_NAME)
            for tr in table.find_elements("tr"):
                rows += [td.text.strip() for td in tr.find_elements("td")]
            # noinspection PyBroadException
            try:
                scraper.find_elements(str(i), self.By.LINK_TEXT)
            except Exception:
                break
            i += 1
        header = rows[0]
        rows = rows[1:]
        return table_type.of(pd.DataFrame(rows, columns=header))


class CachingChemblScrapeApi(ChemblScrapeApi):
    def __init__(
        self,
        query: Optional[QueryingChemblScrapeApi],
        cache_dir: Path = SETTINGS.chembl_cache_path,
    ):
        self._cache_dir = cache_dir
        self._query = query

    def _fetch_page(self, cid: str, page: ChemblScrapePage, table_type: Type[ChemblScrapeTable]):
        path = self.path(cid, page)
        if path.exists():
            return ChemblScrapeTable.read_file(path)
        elif self._query is None:
            return ChemblScrapeTable.new_empty()
        data: TypedDf = self._query._fetch_page(cid, page, table_type)
        data.write_file(path, mkdirs=True)
        logger.debug(f"Scraped page {page} for {cid} with {len(data):,} rows")
        return data

    def path(self, cid: str, page: ChemblScrapePage):
        return (self._cache_dir / page.name / cid).with_suffix(SETTINGS.archive_filename_suffix)


__all__ = [
    "CachingChemblScrapeApi",
    "ChemblScrapeApi",
    "ChemblScrapePage",
    "ChemblScrapePage",
    "ChemblTargetPredictionTable",
    "QueryingChemblScrapeApi",
]
