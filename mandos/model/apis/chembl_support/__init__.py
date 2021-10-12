from __future__ import annotations

from dataclasses import dataclass

from mandos.model import CompoundStruct
from mandos.model.utils import CompoundNotFoundError


class ChemblCompoundLookupError(CompoundNotFoundError):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class ChemblCompound:
    """ """

    chid: str
    inchikey: str
    name: str
    inchi: str

    @property
    def struct_view(self) -> CompoundStruct:
        return CompoundStruct(
            "chembl",
            self.chid,
            self.inchi,
            self.inchikey,
        )


__all__ = [
    "ChemblCompound",
    "ChemblCompoundLookupError",
]
