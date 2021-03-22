"""
Run searches and write files.
"""

from __future__ import annotations

import gzip
import logging
from pathlib import Path
from typing import Sequence, Optional, Dict

import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.path_tools import PathTools
from typeddfs import TypedDfs

from mandos.model import CompoundNotFoundError
from mandos.model.chembl_support.chembl_utils import ChemblUtils
from mandos.model.searches import Search
from mandos.model.settings import MANDOS_SETTINGS
from mandos.search.chembl import ChemblSearch
from mandos.search.pubchem import PubchemSearch
from mandos.entries.api_singletons import Apis

Chembl, Pubchem = Apis.Chembl, Apis.Pubchem
logger = logging.getLogger(__package__)

IdMatchFrame = (
    TypedDfs.typed("IdMatchFrame")
    .require("inchikey")
    .require("chembl_id")
    .require("pubchem_id")
    .strict()
).build()


class SearcherUtils:
    @classmethod
    def dl(
        cls, inchikeys: Sequence[str], pubchem: bool = True, chembl: bool = True
    ) -> IdMatchFrame:
        # we actually cache the results, even though the underlying APIs cache
        # the reasons for this are a little obscure --
        # when running a Searcher, we want to run before the FIRST search
        # for the typer commands to be replicas of the ``Entry.run`` methods, Searcher fetches before running a search
        # but if we have multiple searches (as in ``mandos search --config``), we only want that at the beginning
        # the alternative was having ``mandos search`` dynamically subclass each ``Entry`` -- which was really hard
        # this is much cleaner, even though it's redundant
        # if the cached results under /pubchem and /chembl are deleted, we unfortunately won't cache the results
        # when running this command
        # to fix that, we need to delete the cached /match dataframes
        # now that I'm writing this down, I realize this is pretty bad
        # TODO
        key = hash(",".join(inchikeys))
        cached_path = (MANDOS_SETTINGS.match_cache_path / str(key)).with_suffix(".feather")
        if cached_path.exists():
            logger.info(f"Found ID matching results at {cached_path}")
            return IdMatchFrame.read_feather(cached_path)
        found_chembl: Dict[str, str] = {}
        found_pubchem: Dict[str, str] = {}
        if pubchem:
            for inchikey in inchikeys:
                try:
                    found_pubchem[inchikey] = str(Pubchem.fetch_data(inchikey).cid)
                except CompoundNotFoundError:
                    logger.error(f"Did not find compound {inchikey}")
                    logger.debug(f"Did not find compound {inchikey}", exc_info=True)
        if chembl:
            for inchikey in inchikeys:
                try:
                    found_chembl[inchikey] = ChemblUtils(Chembl).get_compound(inchikey).chid
                except CompoundNotFoundError:
                    logger.error(f"Did not find compound {inchikey}")
                    logger.debug(f"Did not find compound {inchikey}", exc_info=True)
        df = pd.DataFrame([pd.Series(dict(inchikey=c)) for c in inchikeys])
        df["chembl_id"] = df["inchikey"].map(found_chembl.get)
        df["pubchem_id"] = df["inchikey"].map(found_pubchem.get)
        df = IdMatchFrame(df)
        df.to_feather(cached_path)

    @classmethod
    def read(cls, input_path: Path) -> Sequence[str]:
        sep = cls._get_sep(input_path)
        if sep in {"\t", ","}:
            df = pd.read_csv(input_path, sep=sep)
            return cls._from_df(df)
        elif sep == "feather":
            df = pd.read_feather(input_path)
            return cls._from_df(df)
        elif sep == "gz":
            with gzip.open(input_path, "rt") as f:
                return cls._from_txt(f.read())
        elif sep == "txt":
            return cls._from_txt(input_path.read_text(encoding="utf8"))
        else:
            raise AssertionError(sep)

    @classmethod
    def _from_df(cls, df: pd.DataFrame) -> Sequence[str]:
        df.columns = [c.lower() if isinstance(c, str) else c for c in df.columns]
        if "inchikey" not in df.columns:
            raise KeyError("For a CSV or TSV file, include a column called 'inchikey'")
        return df["inchikey"].values.tolist()

    @classmethod
    def _from_txt(cls, text: str) -> Sequence[str]:
        return [line.strip() for line in text.splitlines() if len(line.strip()) > 0]

    @classmethod
    def _get_sep(cls, input_path: Path) -> str:
        if any((str(input_path).endswith(z) for z in {".tab", ".tsv", ".tab.gz", ".tsv.gz"})):
            return "\t"
        elif any((str(input_path).endswith(z) for z in {".csv", ".csv.gz"})):
            return ","
        elif any((str(input_path).endswith(z) for z in {".feather"})):
            return "feather"
        elif any((str(input_path).endswith(z) for z in {".txt.gz", ".lines.gz"})):
            return "gz"
        elif any((str(input_path).endswith(z) for z in {".txt", ".lines"})):
            return "txt"
        else:
            raise ValueError(f"{input_path} should end in .tab, .tsv, .csv, .txt, .lines, or .gz")


class Searcher:
    """
    Executes one or more searches and saves the results to CSV files.
    Create and use once.
    """

    def __init__(self, searches: Sequence[Search], input_path: Path):
        """
        Constructor.

        Args:
            searches:
            input_path: Path to the input file of one of the formats:
                - .txt containing one InChI Key per line
                - .csv, .tsv, .tab, csv.gz, .tsv.gz, .tab.gz, or .feather containing a column called inchikey
        """
        self.what = searches
        self.input_path: Optional[Path] = input_path
        self.inchikeys: Optional[Sequence[str]] = []

    def search(self) -> Searcher:
        """
        Performs the search, and writes data.
        """
        if self.inchikeys is not None:
            raise ValueError(f"Already ran a search")
        self.inchikeys = SearcherUtils.read(self.input_path)
        has_pubchem = any((isinstance(what, PubchemSearch) for what in self.what))
        has_chembl = any((isinstance(what, ChemblSearch) for what in self.what))
        # find the compounds first so the user knows what's missing before proceeding
        SearcherUtils.dl(self.inchikeys, pubchem=has_pubchem, chembl=has_chembl)
        for what in self.what:
            output_path = self.output_path_of(what)
            df = what.find_to_df(self.inchikeys)
            df.to_csv(output_path)
            metadata = NestedDotDict(
                dict(key=what.key, search=what.search_class, params=what.get_params())
            )
            metadata.write_json(output_path.with_suffix(".json"))
        return self

    def paths(self) -> Sequence[Path]:
        return [self.output_path_of(what) for what in self.what]

    def output_path_of(self, what: Search) -> Path:
        parent = self.input_path.parent
        child = self.input_path.stem + what.key + ".tab"
        node = PathTools.sanitize_path_node(child)
        if (parent / node).resolve() != (parent / child).resolve():
            logger.debug(f"Path {child} sanitized to {node}")
        return parent / node


__all__ = ["Searcher", "IdMatchFrame", "SearcherUtils"]
