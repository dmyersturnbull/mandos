"""
PubChem querying API.
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import FrozenSet, Optional, Union

import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import IllegalStateError

from mandos import logger
from mandos.model.apis.pubchem_api import PubchemApi, PubchemCompoundLookupError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi


class CachingPubchemApi(PubchemApi):
    def __init__(self, cache_dir: Path, query: Optional[QueryingPubchemApi]):
        self._cache_dir = cache_dir
        self._querier = query

    def find_id(self, inchikey: str) -> Optional[int]:
        if self.similarity_path(inchikey).exists():
            x = self.fetch_data(inchikey)
            return None if x is None else x.cid
        elif self._querier is not None:
            return self._querier.find_id(inchikey)

    def find_inchikey(self, cid: int) -> Optional[str]:
        if self._querier is None:
            raise IllegalStateError(f"Needs a querying API")
        return self._querier.find_inchikey(cid)

    def fetch_data(self, inchikey: str) -> Optional[PubchemData]:
        path = self.data_path(inchikey)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            logger.debug(f"Found cached PubChem data at {path.absolute()}")
        elif self._querier is None:
            raise PubchemCompoundLookupError(f"{inchikey} not found cached at {path}")
        else:
            try:
                data = self._querier.fetch_data(inchikey)
            except PubchemCompoundLookupError:
                # write an empty dict so we don't query again
                self._write_json(NestedDotDict({}).to_json(), path)
                raise
            encoded = data.to_json()
            self._write_json(encoded, path)
            logger.debug(f"Wrote PubChem data to {path.absolute()}")
            return data
        read = self._read_json(path)
        if len(read) == 0:
            raise PubchemCompoundLookupError(f"{inchikey} is empty at {path}")
        return PubchemData(read)

    def data_path(self, inchikey: str):
        return self._cache_dir / "data" / f"{inchikey}.json.gz"

    def similarity_path(self, inchikey: str):
        return self._cache_dir / "similarity" / f"{inchikey}.snappy"

    def _write_json(self, encoded: str, path: Path) -> None:
        path.write_bytes(gzip.compress(encoded.encode(encoding="utf8")))

    def _read_json(self, path: Path) -> NestedDotDict:
        deflated = gzip.decompress(path.read_bytes())
        read = orjson.loads(deflated)
        return NestedDotDict(read)

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        path = self.similarity_path(inchi)
        if not path.exists():
            df = None
            existing = set()
        else:
            df = pd.read_csv(path, sep="\t")
            df = df[df["min_tc"] < min_tc]
            existing = set(df["cid"].values)
        if len(existing) == 0:
            found = self._querier.find_similar_compounds(inchi, min_tc)
            path.parent.mkdir(parents=True, exist_ok=True)
            new_df = pd.DataFrame([pd.Series(dict(cid=cid, min_tc=min_tc)) for cid in found])
            if df is not None:
                new_df = pd.concat([df, new_df])
            new_df.to_csv(path, sep="\t")
            return frozenset(existing.union(found))
        else:
            return frozenset(existing)


__all__ = ["CachingPubchemApi"]
