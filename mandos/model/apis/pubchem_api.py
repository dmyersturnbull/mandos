"""
PubChem querying API.
"""
from __future__ import annotations

import abc
from typing import Union

import decorateme

from mandos.model import Api, CompoundNotFoundError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData


class PubchemCompoundLookupError(CompoundNotFoundError):
    """ """


@decorateme.auto_repr_str()
class PubchemApi(Api, metaclass=abc.ABCMeta):
    def fetch_data(self, inchikey: Union[str, int]) -> PubchemData:
        """
        Fetches compound data for the given InChI Key.

        Raises:
            PubchemCompoundLookupError: If the compound ID is not found
        """
        raise NotImplementedError()


__all__ = ["PubchemApi", "PubchemCompoundLookupError"]
