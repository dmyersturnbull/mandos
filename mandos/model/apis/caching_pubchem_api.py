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
        path = self.cid_path(cid)
        if path.exists():
            return self._read_inchikey_from_cid(cid)
        elif self._querier is None:
            raise PubchemCompoundLookupError(f"No InChI Key link found at {path}")
        return self._querier.find_inchikey(cid)

    def fetch_data(self, inchikey: Union[str, int]) -> Optional[PubchemData]:
        path = self.data_path(inchikey)
        path.parent.mkdir(parents=True, exist_ok=True)
        cid_path = self.cid_path(inchikey)
        if isinstance(inchikey, int) and cid_path.exists():
            inchikey = self._read_inchikey_from_cid(inchikey)
        elif isinstance(inchikey, int) and self._querier is not None:
            inchikey = self._querier.find_inchikey(inchikey)
            cid_path.write_text(inchikey, encoding="utf8")
        elif isinstance(inchikey, int):
            raise PubchemCompoundLookupError(f"No InChI Key link found at {cid_path}")
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
            cid_path.write_text(inchikey, encoding="utf8")
            logger.debug(f"Wrote PubChem data to {path.absolute()}")
            return data
        read = self._read_json(path)
        if len(read) == 0:
            raise PubchemCompoundLookupError(f"{inchikey} is empty at {path}")
        return PubchemData(read)

    def cid_path(self, cid: int) -> Path:
        return self._cache_dir / "data" / f".{cid}"

    def data_path(self, inchikey: str) -> Path:
        return self._cache_dir / "data" / f"{inchikey}.json.gz"

    def similarity_path(self, inchikey: str) -> Path:
        return self._cache_dir / "similarity" / f"{inchikey}.snappy"

    def _read_inchikey_from_cid(self, cid: int):
        path = self.cid_path(cid)
        if not path.exists():
            raise PubchemCompoundLookupError(f"No InChI Key link found at {path}")
        z = path.read_text(encoding="utf8").strip()
        if len(z) == 0:
            path.unlink()
            raise PubchemCompoundLookupError(f"No InChI Key link found at {path}")
        else:
            return z

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
