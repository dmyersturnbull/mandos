from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TypeVar

from pocketutils.core.exceptions import DownloadError, LookupFailedError
from pocketutils.core.exceptions import MultipleMatchesError as _MME


class Api(metaclass=abc.ABCMeta):
    """ """


class DownloadTimeoutError(DownloadError, TimeoutError):
    """
    User-supplied files.
    """


class DbLookupError(LookupFailedError):
    """"""


class CompoundNotFoundError(DbLookupError):
    """ """


class MultipleMatchesError(_MME):
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
    "CompoundNotFoundError",
    "MultipleMatchesError",
    "DownloadTimeoutError",
]
