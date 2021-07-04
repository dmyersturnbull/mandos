from __future__ import annotations

import enum

from pocketutils.core.dot_dict import NestedDotDict
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from mandos import logger
from mandos.model import CleverEnum, CompoundNotFoundError
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support import ChemblCompound


class MolStructureType(CleverEnum):
    mol = enum.auto()
    both = enum.auto()
    none = enum.auto()


class ChemblUtils:
    def __init__(self, api: ChemblApi):
        self.api = api

    def get_target(self, chembl: str) -> NestedDotDict:
        """
        Queries for the target.

        Args:
            chembl:

        Returns:

        """
        targets = self.api.target.filter(target_chembl_id=chembl)
        if len(targets) != 1:
            raise AssertionError(f"There are {len(targets)} targets: {targets}")
        return NestedDotDict(targets[0])

    def get_compound(self, inchikey: str) -> ChemblCompound:
        """
        Calls ``get_compound_dot_dict`` and then ``compound_dot_dict_to_obj``.

        Args:
            inchikey:

        Returns:

        """
        ch = self.get_compound_dot_dict(inchikey)
        return self.compound_dot_dict_to_obj(ch)

    def compound_dot_dict_to_obj(self, ch: NestedDotDict) -> ChemblCompound:
        """
        Turn results from ``get_compound_dot_dict`` into a ``ChemblCompound``.

        Args:
            ch:

        Returns:

        """
        chid = ch["molecule_chembl_id"]
        mol_type = MolStructureType.of(ch["structure_type"])
        if mol_type == MolStructureType.none:
            logger.info(f"No structure found for compound {chid} of type {mol_type.name}.")
            logger.debug(f"No structure found for compound {ch}.")
            inchikey = "N/A"
        else:
            inchikey = ch["molecule_structures"]["standard_inchi_key"]
        name = ch["pref_name"]
        return ChemblCompound(chid, inchikey, name)

    def get_compound_dot_dict(self, inchikey: str) -> NestedDotDict:
        """
        Fetches info and put into a dict.

        Args:
            inchikey:

        Returns:
            **Only** ``molecule_chembl_id``, ``pref_name``, "and ``molecule_structures`` are guaranteed to exist
        """
        ch = self._get_compound(inchikey)
        # molecule_hierarchy can have the actual value None
        if ch.get("molecule_hierarchy") is not None:
            parent = ch["molecule_hierarchy"]["parent_chembl_id"]
            if parent != ch["molecule_chembl_id"]:
                ch = NestedDotDict(self._get_compound(inchikey))
        return ch

    def _get_compound_from_smiles(self, smiles: str) -> NestedDotDict:
        try:
            results = list(
                self.api.molecule.filter(
                    molecule_structures__canonical_smiles__flexmatch=smiles
                ).only(["molecule_chembl_id", "pref_name", "molecule_structures"])
            )
        except (HTTPError, RequestException):
            raise CompoundNotFoundError(f"NOT FOUND: ChEMBL compound {smiles}")
        if len(results) != 1:
            raise CompoundNotFoundError(f"Got {len(results)} for compound {smiles}")
        result = results[0]
        if result is None:
            raise CompoundNotFoundError(f"Result for compound {smiles} is null!")
        return NestedDotDict(result)

    def _get_compound(self, inchikey: str) -> NestedDotDict:
        try:
            result = self.api.molecule.get(inchikey)
            if result is None:
                raise CompoundNotFoundError(f"Result for compound {inchikey} is null!")
            return NestedDotDict(result)
        except (HTTPError, RequestException):
            raise CompoundNotFoundError(f"Failed to find compound {inchikey}")


__all__ = ["MolStructureType", "ChemblUtils"]
