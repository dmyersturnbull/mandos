import abc
from typing import TypeVar

from pocketutils.core.exceptions import XValueError

from mandos.model.apis.hmdb_api import HmdbApi
from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


class HmdbSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: HmdbApi):
        if api is None:
            raise XValueError(f"{self.__class__.__name__} got a null API")
        super().__init__(key)
        self.api = api


__all__ = ["HmdbSearch"]
