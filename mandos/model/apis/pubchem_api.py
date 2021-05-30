"""
PubChem querying API.
"""
from __future__ import annotations

import abc
from typing import Optional, Union, FrozenSet

from mandos.model import CompoundNotFoundError, Api
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData


class PubchemCompoundLookupError(CompoundNotFoundError):
    """ """


class PubchemApi(Api, metaclass=abc.ABCMeta):
    def fetch_data_from_cid(self, cid: int) -> Optional[PubchemData]:
        # separated from fetch_data to make it completely clear what an int value means
        # noinspection PyTypeChecker
        return self.fetch_data(cid)

    def fetch_data(self, inchikey: str) -> Optional[PubchemData]:
        raise NotImplementedError()

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        raise NotImplementedError()


__all__ = ["PubchemApi", "PubchemCompoundLookupError"]
