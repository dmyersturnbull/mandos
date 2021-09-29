import abc
from typing import Sequence, TypeVar

from pocketutils.core.exceptions import XValueError

from mandos.model.apis.g2p_api import G2pApi
from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


class G2pSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: G2pApi):
        """
        Constructor.

        Args:
            api:
        """
        if api is None:
            raise XValueError(f"{self.__class__.__name__} got a null API")
        super().__init__(key)
        self.api = api


__all__ = ["G2pSearch"]
