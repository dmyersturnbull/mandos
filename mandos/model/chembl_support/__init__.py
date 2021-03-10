from dataclasses import dataclass


@dataclass(frozen=True, order=True, repr=True)
class ChemblCompound:
    """"""

    chid: str
    inchikey: str
    name: str


__all__ = ["ChemblCompound"]
