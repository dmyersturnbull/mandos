"""
PubChem caching API.
"""
from __future__ import annotations

import gzip
import os
from pathlib import Path
from typing import FrozenSet, Optional, Union

import decorateme
import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import XValueError

from mandos.model.apis.pubchem_api import PubchemApi, PubchemCompoundLookupError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi
from mandos.model.settings import SETTINGS
from mandos.model.utils import unlink
from mandos.model.utils.setup import logger


@decorateme.auto_obj()
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
            data = self._read_json(path)
            if data is None:
                raise PubchemCompoundLookupError(
                    f"{inchikey_or_cid} previously not found in PubChem"
                )
            logger.debug(f"Found cached PubChem data for {inchikey_or_cid}: {data.cid}")
            # self._write_siblings(data)  # TODO: remove
            return data
        else:
            logger.debug(f"No cached PubChem data for {inchikey_or_cid}")
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
            logger.info(f"No PubChem compound found for {inchikey_or_cid}")
            logger.trace(f"Wrote empty PubChem data to {path}")
            raise
        cid = data.parent_or_self  # if there's ever a parent of a parent, this will NOT work
        path = self.data_path(cid)
        if path.exists():
            logger.error(f"PubChem data for {inchikey_or_cid} parent CID {cid} exists")
            logger.error(f"Writing over {path} for {inchikey_or_cid}")
        else:
            logger.debug(f"PubChem data for {inchikey_or_cid} parent CID {cid} does not exist")
        data._data.write_json(path, mkdirs=True)
        self._write_siblings(data, inchikey_or_cid)
        logger.debug(f"Wrote PubChem data to {path.resolve()}")
        logger.success(f"Downloaded PubChem data {cid} for {inchikey_or_cid}")
        return data

    def _write_siblings(self, data: PubchemData, *others: str):
        cid = data.parent_or_self
        path = self.data_path(cid)
        aliases = {self.data_path(data.inchikey), *data.siblings, *others}
        for alias in aliases:
            link = self.data_path(alias)
            if link != path and link.resolve() != path.resolve():
                unlink(link, missing_ok=True)
                path.link_to(link)
        logger.debug(f"Added aliases {','.join([str(s) for s in aliases])} ⇌ {cid} ({path})")

    def data_path(self, inchikey_or_cid: Union[int, str]) -> Path:
        return self._cache_dir / "data" / f"{inchikey_or_cid}.json.gz"

    def _read_json(self, path: Path) -> Optional[PubchemData]:
        dot = NestedDotDict.read_json(path)
        return PubchemData(dot) if len(dot) > 0 else None


__all__ = ["CachingPubchemApi"]
