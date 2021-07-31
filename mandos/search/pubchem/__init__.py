import abc
from typing import TypeVar

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
            raise ValueError(self.__class__.__name__)
        super().__init__(key)
        self.api = api


__all__ = ["PubchemSearch"]
