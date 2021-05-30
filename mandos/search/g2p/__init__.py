import abc
from dataclasses import dataclass
from typing import TypeVar

from mandos.model.hits import AbstractHit
from mandos.model.apis.g2p_api import G2pApi
from mandos.model.apis.g2p_data import G2pData, G2pInteraction
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


@dataclass(frozen=True, order=True, repr=True)
class G2pHit(AbstractHit, metaclass=abc.ABCMeta):
    """ """


class G2pSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: G2pApi):
        """
        Constructor.

        Args:
            api:
        """
        if api is None:
            raise ValueError(self.__class__.__name__)
        super().__init__(key)
        self.api = api


__all__ = ["G2pHit", "G2pSearch"]
