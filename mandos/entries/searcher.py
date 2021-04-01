"""
Run searches and write files.
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Sequence, Optional, Dict

import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools
from pocketutils.tools.path_tools import PathTools
from typeddfs import TypedDfs, UntypedDf

from mandos import logger
from mandos.model import CompoundNotFoundError
from mandos.model.chembl_support.chembl_utils import ChemblUtils
from mandos.model.searches import Search
from mandos.model.settings import MANDOS_SETTINGS
from mandos.search.chembl import ChemblSearch
from mandos.search.pubchem import PubchemSearch
from mandos.entries.api_singletons import Apis

InputFrame = (TypedDfs.typed("InputFrame").require("inchikey")).build()

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
        cls,
        inchikeys: Sequence[str],
        pubchem: bool = True,
        chembl: bool = True,
        hmdb: bool = True,
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
        # noinspection PyPep8Naming
        Chembl, Pubchem = Apis.Chembl, Apis.Pubchem
        logger.notice(f"Using {Chembl}, {Pubchem}")
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
                    cid = Pubchem.fetch_data(inchikey).cid
                    found_pubchem[inchikey] = str(cid)
                    logger.info(f"Found:      PubChem {inchikey} ({cid})")
                except CompoundNotFoundError:
                    logger.info(f"NOT FOUND: PubChem {inchikey}")
                    logger.debug(f"Did not find PubChem {inchikey}", exc_info=True)
        if chembl:
            for inchikey in inchikeys:
                try:
                    chid = ChemblUtils(Chembl).get_compound(inchikey).chid
                    found_chembl[inchikey] = chid
                    logger.info(f"Found:      ChEMBL {inchikey} ({chid})")
                except CompoundNotFoundError:
                    logger.info(f"NOT FOUND: ChEMBL {inchikey}")
                    logger.debug(f"Did not find ChEMBL {inchikey}", exc_info=True)
        df = pd.DataFrame([pd.Series(dict(inchikey=c)) for c in inchikeys])
        df["chembl_id"] = df["inchikey"].map(found_chembl.get)
        df["pubchem_id"] = df["inchikey"].map(found_pubchem.get)
        df = IdMatchFrame(df)
        df.to_feather(cached_path)
        logger.info(f"Wrote {cached_path}")

    @classmethod
    def read(cls, input_path: Path) -> InputFrame:
        df: UntypedDf = TypedDfs.untyped("Input").read_file(input_path, header=None, comment="#")
        if "inchikey" in df.column_names():
            df = InputFrame.convert(df)
        elif ".lines" in input_path.name or ".txt" in input_path.name:
            df.columns = ["inchikey"]
            df = InputFrame.convert(df)
        else:
            raise ValueError(f"Could not parse {input_path}; no column 'inchikey'")
        # find duplicates
        # in hindsight, this wasn't worth the amount of code
        n0 = len(df)
        # noinspection PyTypeChecker
        df: UntypedDf = df.drop_duplicates()
        n1 = len(df)
        logger.info("Read {n1} input compounds")
        if n0 == n1:
            logger.info(f"There were no duplicate rows")
        else:
            logger.info(f"Dropped {n1-n0} duplicated rows")
        duplicated = df[df.duplicated("inchikey", keep=False)]
        duplicated_inchikeys = set(duplicated["inchikey"])
        # noinspection PyTypeChecker
        df = df.drop_duplicates(subset=["inchikey"], keep="first")
        n2 = len(df)
        if len(duplicated) > 1:
            logger.error(
                f"{len(duplicated)} rows contain the same inchikey but have differences in other columns"
            )
            logger.error(f"Dropped {n2-n1} rows with duplicate inchikeys")
            logger.error(f"The offending inchikeys are {duplicated_inchikeys}")
        return df


class Searcher:
    """
    Executes one or more searches and saves the results to CSV files.
    Create and use once.
    """

    def __init__(self, searches: Sequence[Search], to: Sequence[Path], input_path: Path):
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
        self.input_df: InputFrame = None
        self.output_paths = {
            what.key: self._output_path_of(what, path)
            for what, path in CommonTools.zip_list(searches, to)
        }

    def search(self) -> Searcher:
        """
        Performs the search, and writes data.
        """
        if self.input_df is not None:
            raise ValueError(f"Already ran a search")
        self.input_df = SearcherUtils.read(self.input_path)
        inchikeys = self.input_df["inchikey"].unique()
        has_pubchem = any((isinstance(what, PubchemSearch) for what in self.what))
        has_chembl = any((isinstance(what, ChemblSearch) for what in self.what))
        # find the compounds first so the user knows what's missing before proceeding
        SearcherUtils.dl(inchikeys, pubchem=has_pubchem, chembl=has_chembl)
        for what in self.what:
            output_path = self.output_paths[what.key]
            df = what.find_to_df(inchikeys)
            # TODO keep any other columns in input_df
            df.to_csv(output_path)
            params = {k: str(v) for k, v in what.get_params().items() if k not in {"key", "api"}}
            metadata = NestedDotDict(dict(key=what.key, search=what.search_class, params=params))
            metadata.write_json(output_path.with_suffix(".json"))
            logger.notice(f"Wrote {what.key} to {output_path}")
        return self

    def _output_path_of(self, what: Search, to: Optional[Path]) -> Path:
        if to is None:
            return self._default_path_of(what)
        elif str(to).startswith("."):
            return self._default_path_of(what).with_suffix(str(to))
        else:
            return to

    def _default_path_of(self, what: Search) -> Path:
        parent = self.input_path.parent / (self.input_path.stem + "-output")
        parent.mkdir(exist_ok=True)
        child = what.key + ".csv"
        node = PathTools.sanitize_path_node(child)
        if (parent / node).resolve() != (parent / child).resolve():
            logger.debug(f"Path {child} sanitized to {node}")
        return parent / node


__all__ = ["Searcher", "IdMatchFrame", "SearcherUtils"]
