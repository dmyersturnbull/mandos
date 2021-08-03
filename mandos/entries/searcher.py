"""
Run searches and write files.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools
from typeddfs import TypedDfs

from mandos import logger
from mandos.entries.api_singletons import Apis
from mandos.entries.paths import EntryPaths
from mandos.model import CompoundNotFoundError
from mandos.model.apis.chembl_support.chembl_utils import ChemblUtils
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.searches import Search
from mandos.search.chembl import ChemblSearch
from mandos.search.pubchem import PubchemSearch


def _get_structure(df) -> Optional[Sequence[str]]:
    if "inchi" in df.columns:
        return df["inchi"].values
    if "smiles" in df.columns:
        return df["smiles"].values
    return None


def _fix_cols(df):
    return df.rename(columns={s: s.lower() for s in df.columns})


InputFrame = (
    TypedDfs.typed("InputFrame")
    .require("inchikey")
    .reserve("inchi", "smiles", "compound_id", dtype=str)
    .post(_fix_cols)
    .strict(index=True, cols=False)
).build()
InputFrame.get_structures = _get_structure


IdMatchFrame = (
    TypedDfs.typed("IdMatchFrame")
    .reserve("inchikey", dtype=str)
    .reserve("inchi", "smiles", "compound_id", dtype=str)
    .reserve("chembl_id", "pubchem_id", "hmdb_id", dtype=str)
    .reserve("origin_inchikey", "origin_smiles", dtype=str)
    .reserve("library", dtype=str)
    .strict(index=True, cols=False)
).build()


@dataclass(frozen=True, repr=True)
class ChemFinder:
    what: str
    how: Callable[[str], str]

    @classmethod
    def chembl(cls) -> ChemFinder:
        def how(inchikey: str) -> str:
            return ChemblUtils(Apis.Chembl).get_compound(inchikey).chid

        return ChemFinder("ChEMBL", how)

    @classmethod
    def pubchem(cls) -> ChemFinder:
        def how(inchikey: str) -> str:
            # noinspection PyTypeChecker
            return Apis.Pubchem.find_id(inchikey)

        return ChemFinder("PubChem", how)

    def find(self, inchikey: str) -> Optional[str]:
        try:
            data = self.how(inchikey)
        except CompoundNotFoundError:
            data = None
            logger.debug(f"Did not find {self.what} {inchikey}", exc_info=True)
        if data is None:
            logger.info(f"NOT FOUND: {self.what.rjust(8)}  ] {inchikey}")
        return str(data)


class SearcherUtils:
    @classmethod
    def dl(
        cls,
        inchikeys: Sequence[str],
        pubchem: bool = True,
        chembl: bool = True,
        hmdb: bool = True,
    ) -> IdMatchFrame:
        df = IdMatchFrame([pd.Series(dict(inchikey=c)) for c in inchikeys])
        if chembl:
            df["chembl_id"] = df["inchikey"].map(ChemFinder.chembl().find)
        if pubchem:
            df["pubchem_id"] = df["inchikey"].map(ChemFinder.pubchem().find)
        return df

    @classmethod
    def read(cls, input_path: Path) -> InputFrame:
        df = InputFrame.read_file(input_path)
        logger.info(f"Read {len(df)} input compounds")
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
            what.key: EntryPaths.output_path_of(what, input_path, path)
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
            metadata_path = output_path.with_suffix(".json.metadata")
            df = what.find_to_df(inchikeys)
            # keep all of the original extra columns from the input
            # e.g. if the user had 'inchi' or 'smiles' or 'pretty_name'
            for extra_col in [c for c in self.input_df.columns if c != "inchikey"]:
                extra_mp = self.input_df.set_index("inchikey")[extra_col].to_dict()
                df[extra_col] = df["lookup"].map(extra_mp.get)
            # write the (intermediate) file
            df.write_file(output_path)
            # write metadata
            params = {k: str(v) for k, v in what.get_params().items() if k not in {"key", "api"}}
            metadata = NestedDotDict(dict(key=what.key, search=what.search_class, params=params))
            metadata.write_json(metadata_path)
            logger.info(f"Wrote {what.key} to {output_path}")
        return self


__all__ = ["Searcher", "IdMatchFrame", "SearcherUtils", "InputFrame"]
