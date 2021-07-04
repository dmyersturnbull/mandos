import abc
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

import defusedxml.ElementTree as Xml
import orjson
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor


class _Source:
    def __init__(self, *getters: Callable[[], Optional[str]], name: str = "unknown"):
        self._getters = getters
        self._name = name

    def _get_txt(self) -> str:
        for getter in self._getters:
            txt = getter()
            if txt is not None:
                return txt
            raise ValueError(f"Nothing found for {self._name} {self.__class__.__name__} source")

    @classmethod
    def cached_from_url(
        cls,
        path: Optional[Path],
        url: Optional[str],
        query: QueryExecutor,
        query_args: Optional[Mapping[str, Any]] = None,
    ):
        if path is not None and url is None and query is None:
            return cls.from_path(path)
        elif path is None and url is not None and query is not None:
            return cls.from_query(url, query, query_args)
        elif path is not None and url is not None and query is not None:
            path = Path(path)
            query_args = {} if query_args is None else query_args

            def load():
                return path.read_text(encoding="utf8") if path.exists() else None

            def save():
                data = query(url, encoding="utf8", **query_args)
                if data is not None:
                    if not path.exists():
                        path.write_text(data, encoding="utf8")
                return data

            # noinspection PyArgumentList
            return cls(load, save, name=f"Cache({path}, {url})")
        raise ValueError(f"Cannot create source from path {path}, url {url}, and query {query}")

    @classmethod
    def from_path(cls, path: Path):
        path = Path(path)

        def one():
            return path.read_text(encoding="utf8") if path.exists() else None

        # noinspection PyArgumentList
        return cls(one, name=f"Cache({path})")

    @classmethod
    def from_query(
        cls, url: str, query: QueryExecutor, query_args: Optional[Mapping[str, Any]] = None
    ):
        def two():
            return query(url, encoding="utf8", **query_args)

        # noinspection PyArgumentList
        return cls(two, name=f"Cache({url})")


class TextSource(_Source):
    def get(self) -> str:
        return self._get_txt()


class XmlSource(_Source):
    """ """

    def get(self) -> Xml:
        return Xml.fromstring(self._get_txt())


class JsonSource(_Source):
    """ """

    def get(self) -> NestedDotDict:
        return NestedDotDict(orjson.loads(self._get_txt()))


__all__ = ["TextSource", "XmlSource", "JsonSource"]
