from __future__ import annotations

import abc
import dataclasses
import enum
import logging
import re
import typing
from dataclasses import dataclass
from typing import Generic, Optional, Sequence, TypeVar

from pocketutils.core.dot_dict import NestedDotDict

from mandos.api import ChemblApi
from mandos.model.caches import TaxonomyCache
from mandos.model.settings import Settings
from mandos.model.taxonomy import Taxonomy

logger = logging.getLogger("mandos")


class MolStructureType(enum.Enum):
    mol = enum.auto()
    both = enum.auto()
    none = enum.auto()

    @classmethod
    def of(cls, s: str) -> MolStructureType:
        return MolStructureType[s.lower()]


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class ChemblCompound:
    """"""

    chid: str
    inchikey: str
    name: str

    @property
    def chid_int(self) -> int:
        return int(self.chid.replace("CHEMBL", ""))


@dataclass(frozen=True, order=True, repr=True)
class AbstractHit:
    """"""

    record_id: Optional[str]
    compound_id: str
    inchikey: str
    compound_lookup: str
    compound_name: str
    object_id: str
    object_name: str

    def to_triple(self) -> Triple:
        return Triple(
            compound_lookup=self.compound_lookup,
            compound_id=self.compound_id,
            compound_name=self.compound_name,
            predicate=self.predicate,
            object_id=self.object_id,
            object_name=self.object_name,
        )

    @property
    def predicate(self) -> str:
        """

        Returns:

        """
        raise NotImplementedError()

    def __hash__(self):
        return hash(self.record_id)

    @classmethod
    def fields(cls) -> Sequence[str]:
        """

        Returns:

        """
        return [f.name for f in dataclasses.fields(cls)]


class QueryType(enum.Enum):
    """
    X
    """

    inchi = enum.auto()
    inchikey = enum.auto()
    chembl = enum.auto()
    smiles = enum.auto()


H = TypeVar("H", bound=AbstractHit, covariant=True)


class Search(Generic[H], metaclass=abc.ABCMeta):
    """"""

    def __init__(self, chembl_api: ChemblApi, config: Settings, tax: Taxonomy):
        """

        Args:
            chembl_api:
            tax:
        """
        self.api = chembl_api
        self.config = config
        self.tax = tax

    @property
    def search_name(self) -> str:
        return self.__class__.__name__.lower().replace("search", "")

    def find_all(self, compounds: Sequence[str]) -> Sequence[H]:
        """

        Args:
            compounds:

        Returns:

        """
        lst = []
        for i, compound in enumerate(compounds):
            x = self.find(compound)
            lst.extend(x)
            logger.debug(f"Found {len(x)} {self.search_name} annotations for {compound}")
            if i % 20 == 0 or i == len(compounds) - 1:
                logger.info(
                    f"Found {len(lst)} {self.search_name} annotations for {i} of {len(compounds)} compounds"
                )
        return lst

    def find(self, compound: str) -> Sequence[H]:
        """

        Args:
            compound:

        Returns:

        """
        raise NotImplementedError()

    @classmethod
    def hit_fields(cls) -> Sequence[str]:
        """

        Returns:

        """
        # Okay, there's a lot of magic going on here
        # We need to access the _parameter_ H on cls -- raw `H` doesn't work
        # get_args and __orig_bases__ do this for us
        # then dataclasses.fields gives us the dataclass fields
        # there's also actual_h.__annotations__, but that doesn't include ClassVar and InitVar
        # (not that we're using those)
        # If this magic is too magical, we can make this an abstract method
        # But that would be a lot of excess code and it might be less modular
        # noinspection PyUnresolvedReferences
        actual_h = typing.get_args(cls.__orig_bases__[0])[0]
        return [f.name for f in dataclasses.fields(actual_h)]

    def get_target(self, chembl: str) -> NestedDotDict:
        """

        Args:
            chembl:

        Returns:

        """
        targets = self.api.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
        return NestedDotDict(targets[0])

    def get_compound(self, inchikey: str) -> ChemblCompound:
        """

        Args:
            inchikey:

        Returns:

        """
        ch = self.get_compound_dot_dict(inchikey)
        return self.compound_dot_dict_to_obj(ch)

    def compound_dot_dict_to_obj(self, ch: NestedDotDict) -> ChemblCompound:
        """

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

    def get_query_type(self, inchikey: str) -> QueryType:
        if inchikey.startswith("InChI="):
            return QueryType.inchi
        elif re.compile(r"[A-Z]{14}-[A-Z]{10}-[A-Z]").fullmatch(inchikey):
            return QueryType.inchikey
        elif re.compile(r"CHEMBL[0-9]+").fullmatch(inchikey):
            return QueryType.chembl
        else:
            return QueryType.smiles

    def get_compound_dot_dict(self, inchikey: str) -> NestedDotDict:
        """

        Args:
            inchikey:

        Returns:
            **Only ``molecule_chembl_id``, ``pref_name``, "and ``molecule_structures`` are guaranteed to exist
        """
        # CHEMBL
        kind = self.get_query_type(inchikey)
        if kind == QueryType.smiles:
            results = list(
                self.api.molecule.filter(
                    molecule_structures__canonical_smiles__flexmatch=inchikey
                ).only(["molecule_chembl_id", "pref_name", "molecule_structures"])
            )
            assert len(results) == 1, f"{len(results)} matches for {inchikey}"
            result = results[0]
        else:
            result = self.api.molecule.get(inchikey)
        if result is None:
            raise ValueError(f"Result for compound {inchikey} is null!")
        ch = NestedDotDict(result)
        # molecule_hierarchy can have the actual value None
        if ch.get("molecule_hierarchy") is not None:
            parent = ch["molecule_hierarchy"]["parent_chembl_id"]
            if parent != ch["molecule_chembl_id"]:
                ch = NestedDotDict(self.api.molecule.get(parent))
        return ch


@dataclass(frozen=True, repr=True, order=True, unsafe_hash=True)
class Triple:
    compound_id: str
    compound_lookup: str
    compound_name: str
    predicate: str
    object_name: str
    object_id: str

    @classmethod
    def tab_header(cls) -> str:
        return "\t".join(
            [
                "compound_id",
                "compound_lookup",
                "compound_name",
                "predicate",
                "object_name",
                "object_id",
            ]
        )

    @property
    def tabs(self) -> str:
        return "\t".join(
            [
                self.compound_lookup,
                self.compound_id,
                self.compound_name,
                self.predicate,
                self.object_name,
                self.object_id,
            ]
        )

    @property
    def statement(self) -> str:
        sub = f"{self.compound_lookup} [{self.compound_id}] [{self.compound_name}]>"
        pred = f"<{self.predicate}>"
        obj = f"<{self.object_name} [{self.object_id}]>"
        return "\t".join([sub, pred, obj])


__all__ = ["ChemblCompound", "AbstractHit", "QueryType", "Search", "Triple"]
