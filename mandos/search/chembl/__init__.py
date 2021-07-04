import abc
from dataclasses import dataclass
from typing import TypeVar

from mandos.model import MiscUtils
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


@dataclass(frozen=True, order=True, repr=True)
class ChemblHit(AbstractHit, metaclass=abc.ABCMeta):
    """ """


class ChemblSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, api: ChemblApi):
        """
        Constructor.

        Args:
            chembl_api:
        """
        super().__init__(key)
        self.api = api


__all__ = ["ChemblHit", "ChemblSearch"]
