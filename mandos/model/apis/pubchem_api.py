"""
PubChem querying API.
"""
from __future__ import annotations

import abc
from typing import FrozenSet, Optional, Union

from mandos.model import Api, CompoundNotFoundError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData


class PubchemCompoundLookupError(CompoundNotFoundError):
    """ """


class PubchemApi(Api, metaclass=abc.ABCMeta):
    def find_id(self, inchikey: str) -> Optional[int]:
        raise NotImplementedError()

    def find_inchikey(self, cid: int) -> Optional[str]:
        raise NotImplementedError()

    def fetch_data(self, inchikey: str) -> Optional[PubchemData]:
        raise NotImplementedError()

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        raise NotImplementedError()


__all__ = ["PubchemApi", "PubchemCompoundLookupError"]
