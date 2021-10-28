"""
Run searches and write files.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Sequence

from pocketutils.core.exceptions import IllegalStateError
from typeddfs import Checksums, TypedDfs

from mandos.model import CompoundNotFoundError
from mandos.model.hit_dfs import HitDf
from mandos.model.hits import AbstractHit
from mandos.model.search_caches import SearchCache
from mandos.model.searches import Search, SearchError
from mandos.model.settings import SETTINGS
from mandos.model.utils.setup import logger


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


@dataclass(frozen=True, repr=True, order=True)
class SearchReturnInfo:
    n_kept: int
    n_processed: int
    n_errored: int
    time_taken: timedelta


@dataclass(frozen=True, repr=True)
class Searcher:
    """
    Executes one or more searches and saves the results.
    Create and use once.
    """

    what: Search
    input_df: InputCompoundsDf
    to: Path
    proceed: bool
    restart: bool

    def search(self) -> SearchReturnInfo:
        """
        Performs the search, and writes data.
        """
        inchikeys = self.input_df["inchikey"].unique()
        if self.is_complete:
            logger.info(f"{self.to} already complete")
            return SearchReturnInfo(
                n_kept=len(inchikeys), n_processed=0, n_errored=0, time_taken=timedelta(seconds=0)
            )
        logger.info(f"Will save every {SETTINGS.save_every} compounds")
        logger.info(f"Writing {self.what.key} to {self.to}")
        annotes = []
        compounds_run = set()
        cache = SearchCache(self.to, inchikeys, restart=self.restart, proceed=self.proceed)
        # refresh so we know it's (no longer) complete
        # this would only happen if we're forcing this -- which is not currently allowed
        (
            Checksums()
            .load_dirsum_of_file(self.to, missing_ok=True)
            .remove(self.to, missing_ok=True)
            .write(rm_if_empty=True)
        )
        t0, n0, n_proc, n_err, n_annot = time.monotonic(), cache.at, 0, 0, 0
        while True:
            try:
                compound = cache.next()
            except StopIteration:
                break
            try:
                with logger.contextualize(compound=compound):
                    x = self.what.find(compound)
                annotes.extend(x)
            except CompoundNotFoundError:
                logger.info(f"Compound {compound} not found for {self.what.key}")
                x = []
                n_err += 1
            except Exception:
                raise SearchError(
                    f"Failed {self.what.key} [{self.what.search_class}] on compound {compound}",
                    compound=compound,
                    search_key=self.what.key,
                    search_class=self.what.search_class,
                )
            compounds_run.add(compound)
            logger.debug(f"Found {len(x)} {self.what.search_name()} annotations for {compound}")
            n_annot += len(x)
            n_proc += 1
            # logging, caching, and such:
            on_nth = cache.at % SETTINGS.save_every == SETTINGS.save_every - 1
            is_last = cache.at == len(inchikeys) - 1
            if on_nth or is_last:
                logger.log(
                    "NOTICE" if is_last else "INFO",
                    f"Found {len(annotes)} {self.what.search_name()} annotations"
                    + f" for {cache.at} of {len(inchikeys)} compounds",
                )
                self._save(annotes, done=is_last)
            cache.save(*compounds_run)  # CRITICAL -- do this AFTER saving
        # done!
        i1, t1 = cache.at, time.monotonic()
        assert i1 == len(inchikeys)
        cache.kill()
        logger.success(f"Wrote {self.what.key} to {self.to}")
        return SearchReturnInfo(
            n_kept=n0, n_processed=n_proc, n_errored=n_err, time_taken=timedelta(seconds=t1 - t0)
        )

    @property
    def is_partial(self) -> bool:
        return self.to.exists() and not self.is_complete

    @property
    def is_complete(self) -> bool:
        done = self.to in Checksums().load_dirsum_of_file(self.to)
        if done and not self.to.exists():
            raise IllegalStateError(f"{self.to} marked complete but does not exist")
        return done

    def _save(self, hits: Sequence[AbstractHit], *, done: bool):
        df = HitDf.from_hits(hits)
        # keep all of the original extra columns from the input
        # e.g. if the user had 'inchi' or 'smiles' or 'pretty_name'
        for extra_col in [c for c in self.input_df.columns if c != "inchikey"]:
            extra_mp = self.input_df.set_index("inchikey")[extra_col].to_dict()
            df[extra_col] = df["origin_inchikey"].map(extra_mp.get)
        # write the file
        df: HitDf = HitDf.of(df)
        params = self.what.get_params()
        df = df.set_attrs(**params, key=self.what.key)
        df.write_file(self.to, mkdirs=True, attrs=True, dir_hash=done)
        logger.debug(f"Saved {len(df)} rows to {self.to}")


__all__ = ["Searcher", "InputCompoundsDf", "SearchReturnInfo"]
