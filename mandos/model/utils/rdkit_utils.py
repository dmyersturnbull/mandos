from __future__ import annotations
from typing import Iterator, List, Set

import numpy as np
from pocketutils.core.exceptions import DataIntegrityError

from mandos.model.utils.setup import logger


try:
    from rdkit import Chem
    from rdkit.Chem import SaltRemover
    from rdkit.Chem import Mol
    import rdkit.Chem.inchi as Inchi
    from rdkit.Chem import AllChem
except ImportError:
    logger.info("rdkit is not installed")
    logger.debug("failed to import rdkit", exc_info=True)
    Chem = None
    Mol = None
    Inchi = None
    SaltRemover = None
    AllChem = None


class MoleculeError(DataIntegrityError):
    pass


class MoleculeConversionError(MoleculeError):
    pass


class NullMoleculeError(MoleculeConversionError):
    pass


class Fingerprint:
    """
    Just a simple wrapper for rdkit fingerprints.
    A bit unnecessary, but convenient when you're using them a lot.
    """

    def __init__(self, fp):
        self._fp = fp

    @property
    def bytes(self) -> bytes:
        return self._fp.ToBinary()

    @property
    def numpy(self) -> np.array:
        # NOTE: frombuffer will NOT work correctly for bool arrays
        # also, fromiter is much slower than creating a list first
        # This is appears to be the fastest way to create an array here
        return np.array(list(self._fp), dtype=bool)

    @property
    def list(self) -> List[bool]:
        return list(map(bool, self._fp))

    @property
    def list_on(self) -> Set[int]:
        self.numpy.nonzero()
        return set(map(bool, self._fp))

    @property
    def string(self) -> str:
        return self._fp.ToBitString()

    @property
    def base64(self) -> str:
        return self._fp.ToBase64()

    @property
    def n_bits(self) -> int:
        return self._fp.GetNumBits()

    @property
    def n_on(self) -> int:
        return self._fp.GetNumOnBits()

    @property
    def n_off(self) -> int:
        return self._fp.GetNumOffBits()

    # TODO: Consider changing to hold bytes or numpy array, and implement | and &
    # def __ror__(self, other: Fingerprint) -> Fingerprint:
    # https://bugs.python.org/issue19251

    def __len__(self) -> int:
        return self._fp.GetNumBits()

    def __str__(self) -> str:
        return self._fp.ToBitString()

    def __repr__(self) -> str:
        return self._fp.ToBitString()

    def __bytes__(self) -> bytes:
        return self._fp.ToBinary()

    def __iter__(self) -> Iterator[bool]:
        return iter(map(bool, self._fp))


class RdkitUtils:
    @classmethod
    def inchikey(cls, inchi_or_smiles: str) -> str:
        inchi = cls.inchi(inchi_or_smiles)
        return Inchi.InchiToInchiKey(inchi)

    @classmethod
    def inchi(cls, inchi_or_smiles: str) -> str:
        if inchi_or_smiles.startswith("InChI="):
            return inchi_or_smiles
        mol = Chem.MolFromSmiles(inchi_or_smiles)
        return Chem.inchi.MolToInchi(mol)

    @classmethod
    def ecfp(cls, inchi_or_smiles: str, radius: int, n_bits: int) -> Fingerprint:
        mol = cls._mol(inchi_or_smiles)
        fp1 = AllChem.GetMorganFingerprintAsBitVect(
            mol, radius=radius, nBits=n_bits, useFeatures=False
        )
        return Fingerprint(fp1)

    @classmethod
    def _mol(cls, inchi_or_smiles: str):
        if inchi_or_smiles.startswith("InChI="):
            return Chem.MolFromInchi(inchi_or_smiles)
        else:
            return Chem.MolFromSmiles(inchi_or_smiles)


__all__ = ["Fingerprint", "RdkitUtils"]
