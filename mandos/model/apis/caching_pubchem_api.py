"""
PubChem caching API.
"""
from __future__ import annotations

import gzip
import os
from pathlib import Path
from typing import FrozenSet, Optional, Union

import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import XValueError

from mandos.model.apis.pubchem_api import PubchemApi, PubchemCompoundLookupError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi
from mandos.model.settings import SETTINGS
from mandos.model.utils.setup import logger


class CachingPubchemApi(PubchemApi):
    def __init__(
        self,
        query: Optional[QueryingPubchemApi],
        cache_dir: Path = SETTINGS.pubchem_cache_path,
    ):
        self._cache_dir = cache_dir
        self._query = query

    def fetch_data(self, inchikey_or_cid: Union[str, int]) -> Optional[PubchemData]:
        path = self.data_path(inchikey_or_cid)
        if path.exists():
            logger.debug(f"Found cached PubChem data")
            data = self._read_json(path)
            if data is None:
                raise PubchemCompoundLookupError(
                    f"{inchikey_or_cid} previously not found in PubChem"
                )
            self._write_siblings(data)  # TODO: remove
            return data
        return self._download(inchikey_or_cid)

    def _download(self, inchikey_or_cid: Union[int, str]) -> PubchemData:
        if self._query is None:
            raise PubchemCompoundLookupError(f"{inchikey_or_cid} not cached")
        # logger.debug(f"Downloading PubChem data for {inchikey_or_cid}")
        try:
            data: PubchemData = self._query.fetch_data(inchikey_or_cid)
        except PubchemCompoundLookupError:
            path = self.data_path(inchikey_or_cid)
            NestedDotDict({}).write_json(path, mkdirs=True)
            logger.debug(f"Wrote empty PubChem data to {path}")
            raise
        cid = data.parent_or_self  # if there's ever a parent of a parent, this will NOT work
        path = self.data_path(cid)
        if path.exists():
            logger.debug(f"PubChem data for {inchikey_or_cid} parent CID {cid} exists")
            logger.caution(f"Writing over {path} for {inchikey_or_cid}")
        else:
            logger.debug(f"PubChem data for {inchikey_or_cid} parent CID {cid} does not exist")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(data.to_json().encode(encoding="utf8")))
        self._write_siblings(data)
        logger.debug(f"Wrote PubChem data to {path.absolute()}")
        logger.info(f"Got PubChem data for {inchikey_or_cid}")
        return data

    def _write_siblings(self, data: PubchemData):
        cid = data.parent_or_self
        path = self.data_path(cid)
        aliases = {self.data_path(data.inchikey), *data.siblings}
        for sibling in aliases:
            link = self.data_path(sibling)
            link.unlink(missing_ok=True)
            path.link_to(link)
        logger.debug(f"Added aliases {','.join([str(s) for s in aliases])} ⇌ {cid} ({path})")

    def data_path(self, inchikey_or_cid: Union[int, str]) -> Path:
        return self._cache_dir / "data" / f"{inchikey_or_cid}.json.gz"

    def _read_json(self, path: Path) -> Optional[PubchemData]:
        dot = NestedDotDict.read_json(path)
        return PubchemData(dot) if len(dot) > 0 else None

    def similarity_path(self, inchi: str, min_tc: float) -> Path:
        if not (min_tc * 100).is_integer():
            raise XValueError(f"min_tc {min_tc} is not an increment of 1%")
        percent = int(min_tc * 100)
        path = self._cache_dir / "similarity" / f"{inchi}_{percent}"
        return path.with_suffix(SETTINGS.archive_filename_suffix)

    def find_similar_compounds(self, inchi: str, min_tc: float) -> FrozenSet[int]:
        logger.debug(f"Searching for {inchi} with min TC {min_tc}")
        path = self.similarity_path(inchi, min_tc)
        if path.exists():
            df = pd.read_file(path)
            return frozenset(set(df["cid"].values))
        found = self._query.find_similar_compounds(inchi, min_tc)
        df = pd.DataFrame([pd.Series(dict(cid=cid)) for cid in found])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.write_file(path)
        logger.debug(f"Wrote {len(df)} values for {inchi} with min TC {min_tc}")
        return frozenset(set(df["cid"].values))


__all__ = ["CachingPubchemApi"]
