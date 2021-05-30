"""
PubChem querying API.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, FrozenSet

import gzip
import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.model.apis.pubchem_api import PubchemCompoundLookupError, PubchemApi
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi


class CachingPubchemApi(PubchemApi):
    def __init__(
        self, cache_dir: Path, querier: Optional[QueryingPubchemApi], compress: bool = True
    ):
        self._cache_dir = cache_dir
        self._querier = querier
        self._compress = compress

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
        ext = ".json.gz" if self._compress else ".json"
        return self._cache_dir / "data" / f"{inchikey}{ext}"

    def similarity_path(self, inchikey: str):
        ext = ".tab.gz" if self._compress else ".tab"
        return self._cache_dir / "similarity" / f"{inchikey}{ext}"

    def _write_json(self, encoded: str, path: Path) -> None:
        if self._compress:
            path.write_bytes(gzip.compress(encoded.encode(encoding="utf8")))
        else:
            path.write_text(encoded, encoding="utf8")

    def _read_json(self, path: Path) -> NestedDotDict:
        if self._compress:
            deflated = gzip.decompress(path.read_bytes())
            read = orjson.loads(deflated)
        else:
            read = orjson.loads(path.read_text(encoding="utf8"))
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
