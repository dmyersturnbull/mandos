from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TypeVar

from pocketutils.core.exceptions import DbLookupError


class Api(metaclass=abc.ABCMeta):
    """ """


T = TypeVar("T", covariant=True)


@dataclass(frozen=True, repr=True, order=True)
class CompoundStruct:
    """
    Uniform data view for ChEMBL, PubChem, etc.
    Contains the source db (e.g. "pubchem"), the ID as a str, the inchi, and the inchikey.
    """

    db: str
    id: str
    inchi: str
    inchikey: str

    @property
    def simple_str(self) -> str:
        db = "" if self.db.lower() == "chembl" else self.db + " "
        return f"[{db}{self.id} : {self.inchikey}]"


__all__ = [
    "Api",
    "CompoundStruct",
]


class CompoundNotFoundError(DbLookupError):
    """ """
