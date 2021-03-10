import abc
from dataclasses import dataclass
from typing import TypeVar

from mandos.model.hits import AbstractHit
from mandos.model.pubchem_api import PubchemApi
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


@dataclass(frozen=True, order=True, repr=True)
class PubchemHit(AbstractHit, metaclass=abc.ABCMeta):
    """"""


class PubchemSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, pubchem_api: PubchemApi):
        """
        Constructor.

        Args:
            pubchem_api:
        """
        self.api = pubchem_api


__all__ = ["PubchemHit", "PubchemSearch"]
