"""
PubChem querying API.
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import FrozenSet, Optional, Union, Sequence

import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import IllegalStateError

from mandos import logger, MANDOS_SETTINGS
from mandos.model.apis.pubchem_api import PubchemApi, PubchemCompoundLookupError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi


class CachingPubchemApi(PubchemApi):
    def __init__(
        self,
        query: Optional[QueryingPubchemApi],
        cache_dir: Path = MANDOS_SETTINGS.pubchem_cache_path,
    ):
        self._cache_dir = cache_dir
        self._query = query
        self._add_all_cids()

    def find_id(self, inchikey: str) -> Optional[int]:
        if self.similarity_path(inchikey).exists():
            x = self.fetch_data(inchikey)
            return None if x is None else x.cid
        elif self._query is not None:
            return self._query.find_id(inchikey)

    def find_inchikey(self, cid: int) -> Optional[str]:
        path = self.cid_path(cid)
        if path.exists():
            return self._read_inchikey_from_cid(cid)
        elif self._query is None:
            raise PubchemCompoundLookupError(f"No InChI Key link found at {path}")
        return self._query.find_inchikey(cid)

    def fetch_data(self, inchikey: Union[str, int]) -> Optional[PubchemData]:
        path = self.data_path(inchikey)
        path.parent.mkdir(parents=True, exist_ok=True)
        cid_path = self.cid_path(inchikey)
        if isinstance(inchikey, int) and cid_path.exists():
            cid = inchikey
            inchikey = self._read_inchikey_from_cid(inchikey)
        elif isinstance(inchikey, int) and self._query is not None:
            cid = inchikey
            inchikey = self._query.find_inchikey(inchikey)
            self._add_cid(cid, inchikey)
            cid_path.write_text(inchikey, encoding="utf8")
        elif isinstance(inchikey, int):
            raise PubchemCompoundLookupError(f"No InChI Key link found at {cid_path}")
        if path.exists():
            logger.debug(f"Found cached PubChem data at {path.absolute()}")
        elif self._query is None:
            raise PubchemCompoundLookupError(f"{inchikey} not found cached at {path}")
        else:
            try:
                data = self._query.fetch_data(inchikey)
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

    def list_data(self) -> Sequence[Path]:
        return {
            p.name.replace(".json.gz", ""): p for p in (self._cache_dir / "data").glob("*.json.gz")
        }

    def cid_path(self, cid: int) -> Path:
        return self._cache_dir / "cids" / f"{cid}.txt"

    def data_path(self, inchikey: str) -> Path:
        return self._cache_dir / "data" / f"{inchikey}.json.gz"

    def similarity_path(self, inchikey: str) -> Path:
        return self._cache_dir / "similarity" / f"{inchikey}.snappy"

    def _add_all_cids(self):
        # not normally needed, but we run this for mainly historical reasons
        logger.info(f"Adding missing CID links.")
        for inchikey, path in self.list_data():
            data = self.fetch_data(inchikey)
            cid = data.cid
            self._add_cid(cid, inchikey)

    def _add_cid(self, cid: int, inchikey: str):
        cid_path = self.cid_path(cid)
        cid_path.parent.mkdir(parents=True, exist_ok=True)
        if cid_path.exists():
            loaded_inchikey = self._read_inchikey_from_cid(cid)
            if loaded_inchikey != inchikey:
                logger.error(
                    f"For {cid}, existing entry points to {loaded_inchikey}, not {inchikey}. Overwriting."
                )
        cid_path.write_text(inchikey, encoding="utf8")

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
            found = self._query.find_similar_compounds(inchi, min_tc)
            path.parent.mkdir(parents=True, exist_ok=True)
            new_df = pd.DataFrame([pd.Series(dict(cid=cid, min_tc=min_tc)) for cid in found])
            if df is not None:
                new_df = pd.concat([df, new_df])
            new_df.to_csv(path, sep="\t")
            return frozenset(existing.union(found))
        else:
            return frozenset(existing)


__all__ = ["CachingPubchemApi"]
