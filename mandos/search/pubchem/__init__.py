import abc
from typing import TypeVar

from pocketutils.core.exceptions import XValueError

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


class PubchemSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: PubchemApi):
        """
        Constructor.

        Args:
            api:
        """
        if api is None:
            raise XValueError(f"{self.__class__.__name__} got a null API")
        super().__init__(key)
        self.api = api


__all__ = ["PubchemSearch"]
