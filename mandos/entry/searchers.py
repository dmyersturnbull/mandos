"""
Run searches and write files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools
from typeddfs import TypedDfs

from mandos import logger
from mandos.entry.paths import EntryPaths
from mandos.model.searches import Search


def _fix_cols(df):
    return df.rename(columns={s: s.lower() for s in df.columns})


InputFrame = (
    TypedDfs.typed("InputFrame")
    .require("inchikey")
    .reserve("inchi", "smiles", "compound_id", dtype=str)
    .post(_fix_cols)
    .strict(cols=False)
    .secure()
).build()


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
        self.input_df = InputFrame.read_file(self.input_path)
        logger.info(f"Read {len(self.input_df)} input compounds")
        inchikeys = self.input_df["inchikey"].unique()
        for what in self.what:
            self._search_one(what, inchikeys)
        return self

    def _search_one(self, what: Search, inchikeys: Sequence[str]):
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


__all__ = ["Searcher", "InputFrame"]
