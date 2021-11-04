import abc
import time
import urllib
from pathlib import Path
from typing import Optional
from urllib import request

import decorateme
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor

from mandos.model import Api, CompoundNotFoundError
from mandos.model.apis.hmdb_support.hmdb_data import HmdbData
from mandos.model.settings import QUERY_EXECUTORS, SETTINGS
from mandos.model.utils.setup import logger


class HmdbCompoundLookupError(CompoundNotFoundError):
    """ """


@decorateme.auto_repr_str()
class HmdbApi(Api, metaclass=abc.ABCMeta):
    def fetch(self, hmdb_id: str) -> HmdbData:
        raise NotImplementedError()


@decorateme.auto_repr_str()
class QueryingHmdbApi(HmdbApi):
    def __init__(self, executor: QueryExecutor = QUERY_EXECUTORS.hmdb):
        self._executor = executor

    def fetch(self, inchikey_or_hmdb_id: str) -> HmdbData:
        logger.debug(f"Downloading HMDB data for {inchikey_or_hmdb_id}")
        # e.g. https://hmdb.ca/metabolites/HMDB0001925.xml
        cid = None
        if inchikey_or_hmdb_id.startswith("HMDB"):
            cid = inchikey_or_hmdb_id
        else:
            time.sleep(SETTINGS.hmdb_query_delay_min)  # TODO
            url = f"https://hmdb.ca/unearth/q?query={inchikey_or_hmdb_id}&searcher=metabolites"
            try:
                res = urllib.request.urlopen(url)
                url_ = res.geturl()
                logger.trace(f"Got UR {url_} from {url}")
                cid = url_.split("/")[-1]
                if not cid.startswith("HMDB"):
                    raise ValueError(f"Invalid CID {cid} from URL {url_}")
            except Exception:
                raise HmdbCompoundLookupError(f"No HMDB match for {inchikey_or_hmdb_id}")
        url = f"https://hmdb.ca/metabolites/{cid}.xml"
        try:
            data = self._executor(url)
        except Exception:
            raise HmdbCompoundLookupError(f"No HMDB match for {inchikey_or_hmdb_id} ({cid})")
        return HmdbData(self._to_json(data))

    def _to_json(self, xml) -> NestedDotDict:
        response = {}
        for child in list(xml):
            if len(list(child)) > 0:
                response[child.tag] = self._to_json(child)
            else:
                response[child.tag] = child.text or ""
        return NestedDotDict(response)

    def _query(self, url: str) -> str:
        data = self._executor(url)
        tt = self._executor.last_time_taken
        wt, qt = tt.wait.total_seconds(), tt.query.total_seconds()
        bts = int(len(data) * 8 / 1024)
        logger.trace(f"Queried {bts} kb from {url} in {qt:.1} s with {wt:.1} s of wait")
        return data


@decorateme.auto_repr_str()
class CachingHmdbApi(HmdbApi):
    def __init__(
        self, query: Optional[QueryingHmdbApi], cache_dir: Path = SETTINGS.hmdb_cache_path
    ):
        self._query = query
        self._cache_dir = cache_dir

    def path(self, inchikey_or_hmdb_id: str) -> Path:
        return self._cache_dir / f"{inchikey_or_hmdb_id}.json.gz"

    def fetch(self, inchikey_or_hmdb_id: str) -> HmdbData:
        path = self.path(inchikey_or_hmdb_id)
        if path.exists():
            return HmdbData(NestedDotDict.read_json(path))
        else:
            data = self._query.fetch(inchikey_or_hmdb_id)
            path = self.path(data.cid)
            data._data.write_json(path, mkdirs=True)
            logger.info(f"Saved HMDB metabolite {data.cid}")
            self._write_links(data)
            return data

    def _write_links(self, data: HmdbData) -> None:
        path = self.path(data.cid)
        # these all have different prefixes, so it's ok
        aliases = [
            data.inchikey,
            *[ell for ell in [data.cas, data.pubchem_id, data.drugbank_id] if ell is not None],
        ]
        for alias in aliases:
            link = self.path(alias)
            link.unlink(missing_ok=True)
            path.link_to(link)
        logger.debug(f"Added aliases {','.join([str(s) for s in aliases])} ⇌ {data.cid} ({path})")


__all__ = [
    "HmdbApi",
    "QueryingHmdbApi",
    "CachingHmdbApi",
    "HmdbCompoundLookupError",
]
