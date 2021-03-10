from typing import TypeVar
import abc
from dataclasses import dataclass

from mandos.model.chembl_api import ChemblApi
from mandos.model.taxonomy import Taxonomy
from mandos.model.searches import Search
from mandos.model.hits import AbstractHit


H = TypeVar("H", bound=AbstractHit, covariant=True)


@dataclass(frozen=True, order=True, repr=True)
class ChemblHit(AbstractHit, metaclass=abc.ABCMeta):
    """"""


class ChemblSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, chembl_api: ChemblApi):
        """
        Constructor.

        Args:
            chembl_api:
        """
        self.api = chembl_api


__all__ = ["ChemblHit", "ChemblSearch"]
