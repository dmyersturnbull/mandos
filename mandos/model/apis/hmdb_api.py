import abc
import gzip
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

import decorateme
import orjson
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor
from pocketutils.tools.common_tools import CommonTools

from mandos.model import Api
from mandos.model.settings import QUERY_EXECUTORS, SETTINGS


@dataclass(frozen=True, repr=True, order=True)
class HmdbProperty:
    name: str
    source: str
    value: Union[None, str, int, float, bool]
    experimental: bool


@decorateme.auto_repr_str()
class HmdbApi(Api, metaclass=abc.ABCMeta):
    def fetch(self, hmdb_id: str) -> NestedDotDict:
        raise NotImplementedError()

    def fetch_properties(self, hmdb_id: str) -> Sequence[HmdbProperty]:
        raise NotImplementedError()

    def fetch_tissues(self, hmdb_id: str) -> Sequence[HmdbProperty]:
        raise NotImplementedError()


class JsonBackedHmdbApi(HmdbApi, metaclass=abc.ABCMeta):
    def fetch_properties(self, hmdb_id: str) -> Sequence[HmdbProperty]:
        data = self.fetch(hmdb_id)
        pred = data.sub("metabolite.predicted_properties.property")
        exp = data.sub("metabolite.experimental_properties.property")
        items = [self._prop(x, True) for x in exp]
        items += [self._prop(x, False) for x in pred]
        return items

    def fetch_tissues(self, hmdb_id: str) -> Sequence[str]:
        data = self.fetch(hmdb_id)
        tissues = data.get_list_as("metabolite.biological_properties.tissue_locations.tissue", str)
        return [] if tissues is None else tissues

    def _prop(self, x: NestedDotDict, experimental: bool):
        value = x.req_as("value", str)
        if value.isdigit():
            value = int(value)
        elif value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif CommonTools.is_probable_null(value):
            value = None
        elif CommonTools.is_float(value):
            value = float(value)
        return HmdbProperty(
            name=x["kind"], value=value, source=x["source"], experimental=experimental
        )


class QueryingHmdbApi(JsonBackedHmdbApi):
    def __init__(self, executor: QueryExecutor = QUERY_EXECUTORS.hmdb):
        self._executor = executor

    def fetch(self, hmdb_id: str) -> NestedDotDict:
        # e.g. https://hmdb.ca/metabolites/HMDB0001925.xml
        url = f"https://hmdb.ca/metabolites/{hmdb_id}.xml"
        data = self._executor(url)
        data = self._to_json(data)
        return NestedDotDict(data)

    def _to_json(self, xml):
        response = {}
        for child in list(xml):
            if len(list(child)) > 0:
                response[child.tag] = self._to_json(child)
            else:
                response[child.tag] = child.text or ""
        return response


class CachingHmdbApi(JsonBackedHmdbApi):
    def __init__(
        self, query: Optional[QueryingHmdbApi], cache_dir: Path = SETTINGS.hmdb_cache_path
    ):
        self._query = query
        self._cache_dir = cache_dir

    def fetch(self, hmdb_id: str) -> NestedDotDict:
        path = self.path(hmdb_id)
        if not path.exists():
            return NestedDotDict.read_json(path)
        else:
            data = self._query.fetch(hmdb_id)
            data.write_json(path, mkdirs=True)
            self._write_json(data, path)
            return data


__all__ = ["HmdbApi", "QueryingHmdbApi", "HmdbProperty"]
