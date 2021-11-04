"""
API for PubChem similarity search.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import FrozenSet

import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import DownloadTimeoutError, XValueError
from pocketutils.core.query_utils import QueryExecutor
from typeddfs import TypedDfs

from mandos.model.apis.similarity_api import SimilarityApi
from mandos.model.settings import QUERY_EXECUTORS, SETTINGS
from mandos.model.utils.setup import logger

SimilarityDf = (TypedDfs.typed("SimilarityDf").require("cid", dtype=int).secure()).build()


class QueryingPubchemSimilarityApi(SimilarityApi):
    def __init__(self, executor: QueryExecutor = QUERY_EXECUTORS.pubchem):
        self._executor = executor

    _pug = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def search(self, inchi: str, min_tc: float) -> FrozenSet[int]:
        req = self._executor(
            f"{self._pug}/compound/similarity/inchikey/{inchi}/JSON?Threshold={min_tc}",
            method="post",
        )
        key = orjson.loads(req)["Waiting"]["ListKey"]
        t0 = time.monotonic()
        while time.monotonic() - t0 < 5:
            # it'll wait as needed here
            resp = self._executor(f"{self._pug}/compound/listkey/{key}/cids/JSON")
            resp = NestedDotDict(orjson.loads(resp))
            if resp.get("IdentifierList.CID") is not None:
                return frozenset(resp.req_list_as("IdentifierList.CID", int))
        raise DownloadTimeoutError(f"Search for {inchi} using key {key} timed out")


class CachingPubchemSimilarityApi(SimilarityApi):
    def __init__(self, query: QueryingPubchemSimilarityApi):
        self._query = query

    def path(self, inchi: str, min_tc: float) -> Path:
        if not (min_tc * 100).is_integer():
            raise XValueError(f"min_tc {min_tc} is not an increment of 1%")
        percent = int(min_tc * 100)
        path = self._cache_dir / "similarity" / f"{inchi}_{percent}"
        return path.with_suffix(SETTINGS.archive_filename_suffix)

    def search(self, inchi: str, min_tc: float) -> FrozenSet[int]:
        logger.info(f"Searching for {inchi} with min TC {min_tc}")
        path = self.path(inchi, min_tc)
        if path.exists():
            df = SimilarityDf.read_file(path)
            return frozenset(set(df["cid"].values))
        found = self._query.search(inchi, min_tc)
        df: SimilarityDf = SimilarityDf.of([pd.Series(dict(cid=cid)) for cid in found])
        df.write_file(path.resolve(), mkdirs=True, dir_hash=True)
        logger.info(f"Wrote {len(df)} values for {inchi} with min TC {min_tc}")
        return frozenset(set(df["cid"].values))


__all__ = ["QueryingPubchemSimilarityApi", "CachingPubchemSimilarityApi"]
