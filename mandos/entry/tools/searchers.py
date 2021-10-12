"""
Run searches and write files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import IllegalStateError
from pocketutils.tools.common_tools import CommonTools
from typeddfs import TypedDfs
from typeddfs.checksums import Checksums

from mandos import logger
from mandos.model.hit_dfs import HitDf
from mandos.model.hits import AbstractHit
from mandos.model.search_caches import SearchCache
from mandos.model.searches import Search, SearchError
from mandos.model.settings import SETTINGS
from mandos.model.utils import CompoundNotFoundError


def _fix_cols(df):
    return df.rename(columns={s: s.lower() for s in df.columns})


InputCompoundsDf = (
    TypedDfs.typed("InputCompoundsDf")
    .require("inchikey")
    .reserve("inchi", "smiles", "compound_id", dtype=str)
    .post(_fix_cols)
    .strict(cols=False)
    .secure()
).build()


class Searcher:
    """
    Executes one or more searches and saves the results.
    Create and use once.
    """

    def __init__(self, searches: Sequence[Search], to: Sequence[Path], input_path: Path):
        self.what = searches
        self.input_path: Optional[Path] = input_path
        self.input_df: InputCompoundsDf = None
        self.output_paths = {what.key: path for what, path in CommonTools.zip_list(searches, to)}

    def search(self) -> Searcher:
        """
        Performs the search, and writes data.
        """
        if self.input_df is not None:
            raise IllegalStateError(f"Already ran a search")
        self.input_df = InputCompoundsDf.read_file(self.input_path)
        logger.info(f"Read {len(self.input_df)} input compounds")
        inchikeys = self.input_df["inchikey"].unique()
        for what in self.what:
            output_path = self.output_paths[what.key]
            self._search_one(what, inchikeys, output_path)
        return self

    def _search_one(self, search: Search, inchikeys: Sequence[str], path: Path) -> None:
        """
        Loops over every compound and calls ``find``.
        Comes with better logging.
        Writes a logging ERROR for each compound that was not found.

        Args:
            inchikeys: A list of InChI key strings
            path: Path to write to
        """
        logger.info(f"Will save every {SETTINGS.save_every} compounds")
        logger.info(f"Writing {search.key} to {path}")
        annotes = []
        compounds_run = set()
        cache = SearchCache(path, inchikeys)
        # refresh so we know it's (no longer) complete
        Checksums.delete_dir_hashes(Checksums.get_hash_dir(path), [path], missing_ok=True)
        self._save_metadata(path, search)
        while True:
            try:
                compound = cache.next()
            except StopIteration:
                break
            try:
                with logger.contextualize(compound=compound):
                    x = search.find(compound)
                annotes.extend(x)
            except CompoundNotFoundError:
                logger.info(f"Compound {compound} not found for {search.key}")
                x = []
            except Exception:
                raise SearchError(
                    f"Failed {search.key} [{search.search_class}] on compound {compound}",
                    compound=compound,
                    search_key=search.key,
                    search_class=search.search_class,
                )
            compounds_run.add(compound)
            logger.debug(f"Found {len(x)} {search.search_name()} annotations for {compound}")
            # logging, caching, and such:
            on_nth = cache.at % SETTINGS.save_every == SETTINGS.save_every - 1
            is_last = cache.at == len(inchikeys) - 1
            if on_nth or is_last:
                logger.log(
                    "NOTICE" if is_last else "INFO",
                    f"Found {len(annotes)} {search.search_name()} annotations"
                    + f" for {cache.at} of {len(inchikeys)} compounds",
                )
                self._save_annotations(annotes, path, done=is_last)
            cache.save(*compounds_run)  # CRITICAL -- do this AFTER saving
        # done!
        cache.kill()
        logger.info(f"Wrote {search.key} to {path}")

    def _save_annotations(self, hits: Sequence[AbstractHit], output_path: Path, *, done: bool):
        df = HitDf.from_hits(hits)
        # keep all of the original extra columns from the input
        # e.g. if the user had 'inchi' or 'smiles' or 'pretty_name'
        for extra_col in [c for c in self.input_df.columns if c != "inchikey"]:
            extra_mp = self.input_df.set_index("inchikey")[extra_col].to_dict()
            df[extra_col] = df["origin_inchikey"].map(extra_mp.get)
        # write the file
        df = HitDf.of(df)
        df.write_file(output_path, mkdirs=True, dir_hash=done)

    def _save_metadata(self, output_path: Path, search: Search):
        metadata_path = output_path.with_suffix(".metadata.json")
        params = {k: str(v) for k, v in search.get_params().items() if k not in {"key", "api"}}
        metadata = NestedDotDict(dict(key=search.key, search=search.search_class, params=params))
        metadata.write_json(metadata_path, indent=True)


__all__ = ["Searcher", "InputCompoundsDf"]
