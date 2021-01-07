from __future__ import annotations

import abc
import dataclasses
import enum
import logging
import typing
from dataclasses import dataclass
from typing import Generic, Optional, Sequence, TypeVar

from urllib3.exceptions import HTTPError
from requests.exceptions import RequestException
from pocketutils.core.dot_dict import NestedDotDict

from mandos import MandosUtils, QueryType
from mandos.chembl_api import ChemblApi
from mandos.model.settings import Settings
from mandos.model.taxonomy import Taxonomy

logger = logging.getLogger("mandos")


class CompoundNotFoundError(ValueError):
    """"""


class MolStructureType(enum.Enum):
    mol = enum.auto()
    both = enum.auto()
    none = enum.auto()

    @classmethod
    def of(cls, s: str) -> MolStructureType:
        return MolStructureType[s.lower()]


@dataclass(frozen=True, order=True, repr=True)
class ChemblCompound:
    """"""

    chid: str
    inchikey: str
    name: str


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


H = TypeVar("H", bound=AbstractHit, covariant=True)


class Search(Generic[H], metaclass=abc.ABCMeta):
    """
    Something to search and how to do it.
    """

    def __init__(self, chembl_api: ChemblApi, config: Settings, tax: Taxonomy):
        """
        Constructor.

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
        Loops over every compound and calls ``find``.
        Just comes with better logging.

        Args:
            compounds:

        Returns:

        """
        lst = []
        for i, compound in enumerate(compounds):
            try:
                x = self.find(compound)
            except CompoundNotFoundError:
                logger.error(f"Failed to find compound {compound}. Skipping.")
                continue
            lst.extend(x)
            logger.debug(f"Found {len(x)} {self.search_name} annotations for {compound}")
            if i > 0 and i % 20 == 0 or i == len(compounds) - 1:
                logger.info(
                    f"Found {len(lst)} {self.search_name} annotations for {i} of {len(compounds)} compounds"
                )
        return lst

    def find(self, compound: str) -> Sequence[H]:
        """
        To override.

        Args:
            compound:

        Returns:
            Something

        Raises:
            CompoundNotFoundError
        """
        raise NotImplementedError()

    @classmethod
    def hit_fields(cls) -> Sequence[str]:
        """
        Gets the fields in the Hit type parameter.

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
        actual_h = typing.get_args(cls.get_h())[0]
        return [f.name for f in dataclasses.fields(actual_h)]

    @classmethod
    def get_h(cls):
        """
        What is my hit type?

        Returns:

        """
        # noinspection PyUnresolvedReferences
        return cls.__orig_bases__[0]

    def get_target(self, chembl: str) -> NestedDotDict:
        """
        Queries for the target.

        Args:
            chembl:

        Returns:

        """
        targets = self.api.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
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

    def get_query_type(self, inchikey: str) -> QueryType:
        """
        Returns the type of query.

        Args:
            inchikey:

        Returns:

        """
        return MandosUtils.get_query_type(inchikey)

    def get_compound_dot_dict(self, inchikey: str) -> NestedDotDict:
        """
        Fetches info and put into a dict.

        Args:
            inchikey:

        Returns:
            **Only** ``molecule_chembl_id``, ``pref_name``, "and ``molecule_structures`` are guaranteed to exist
        """
        # CHEMBL
        kind = self.get_query_type(inchikey)
        if kind == QueryType.smiles:
            ch = self._get_compound_from_smiles(inchikey)
        else:
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
            raise CompoundNotFoundError(f"Failed to find compound {smiles}")
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


@dataclass(frozen=True, repr=True, order=True)
class Triple:
    """
    Compound, predicate, object.
    """

    compound_id: str
    compound_lookup: str
    compound_name: str
    predicate: str
    object_name: str
    object_id: str

    @classmethod
    def tab_header(cls) -> str:
        """

        Returns:

        """
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
        items = [
            self.compound_lookup,
            self.compound_id,
            self.compound_name,
            self.predicate,
            self.object_name,
            self.object_id,
        ]
        return "\t".join(["-" if k is None else str(k) for k in items])

    @property
    def statement(self) -> str:
        """
        Returns a simple text statement with brackets.

        Returns:

        """
        sub = f"{self.compound_lookup} [{self.compound_id}] [{self.compound_name}]>"
        pred = f"<{self.predicate}>"
        obj = f"<{self.object_name} [{self.object_id}]>"
        return "\t".join([sub, pred, obj])


__all__ = [
    "ChemblCompound",
    "AbstractHit",
    "QueryType",
    "Search",
    "Triple",
    "CompoundNotFoundError",
]
