"""
PubChem querying API.
"""
from __future__ import annotations

import gzip
from pathlib import Path
from typing import FrozenSet, Optional, Union, Set

import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.model.settings import MANDOS_SETTINGS
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

    def follow_link(self, inchikey_or_cid: Union[int, str]) -> Optional[Path]:
        link = self.link_path(inchikey_or_cid)
        cid = link.read_text(encoding="utf8").strip()
        if len(cid) == 0:
            return None
        return self.data_path(int(cid))

    def get_links(self, cid: int) -> Set[Path]:
        data = self._read_json(self.data_path(cid))
        siblings = set(data.siblings)
        for sibling in siblings:
            sibling_path = self.follow_link(sibling)
            if sibling_path is not None:
                inchikey_siblings = self._read_json(sibling_path).siblings
                siblings.update(inchikey_siblings)
        links = {data.inchikey, data.cid, *siblings}
        return {self.link_path(link) for link in links}

    def fetch_data(self, inchikey_or_cid: Union[str, int]) -> Optional[PubchemData]:
        followed = self.follow_link(inchikey_or_cid)
        if followed is not None:
            logger.debug(f"Found cached PubChem data")
            return self._read_json(followed)
        return self._download(inchikey_or_cid)

    def _download(self, inchikey_or_cid: Union[int, str]) -> PubchemData:
        if self._query is None:
            raise PubchemCompoundLookupError(f"{inchikey_or_cid} not cached")
        data: PubchemData = self._query.fetch_data(inchikey_or_cid)
        cid = data.parent_or_self
        path = self.data_path(cid)
        self._write_json(data.to_json(), path)
        links = {inchikey_or_cid, *self.get_links(cid)}
        for link in links:
            if not link.exists():
                link.write_text(str(cid), encoding="utf8")
        logger.debug(f"Wrote PubChem data to {path.absolute()}")
        return data

    def link_path(self, inchikey_or_cid: Union[int, str]) -> Path:
        return self._cache_dir / "links" / f"{inchikey_or_cid}.txt"

    def data_path(self, cid: int) -> Path:
        return self._cache_dir / "data" / f"{cid}.json.gz"

    def similarity_path(self, inchi: str, min_tc: float) -> Path:
        if not (min_tc * 100).is_integer():
            raise ValueError(f"min_tc {min_tc} is not an increment of 1%")
        percent = int(min_tc * 100)
        path = self._cache_dir / "similarity" / f"{inchi}_{percent}"
        return path.with_suffix(MANDOS_SETTINGS.archive_filename_suffix)

    def _write_json(self, encoded: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(encoded.encode(encoding="utf8")))

    def _read_json(self, path: Path) -> Optional[PubchemData]:
        deflated = gzip.decompress(path.read_bytes())
        read = orjson.loads(deflated)
        return PubchemData(NestedDotDict(read)) if len(read) > 0 else None

    def find_similar_compounds(self, inchi: str, min_tc: float) -> FrozenSet[int]:
        path = self.similarity_path(inchi, min_tc)
        if path.exists():
            df = pd.read_file(path)
            return frozenset(set(df["cid"].values))
        found = self._query.find_similar_compounds(inchi, min_tc)
        df = pd.DataFrame([pd.Series(dict(cid=cid)) for cid in found])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.write_file(path)
        return frozenset(set(df["cid"].values))


__all__ = ["CachingPubchemApi"]
