from __future__ import annotations

import abc
import dataclasses
import logging
import typing
from dataclasses import dataclass
from typing import Generic, Optional, Sequence, TypeVar

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.taxonomy import Taxonomy
from mandos.model.utils import Utils

logger = logging.getLogger("mandos")


class ChemblEntrypoint:
    """
    Wraps just part of a node in the ChEMBL REST API.
    Ex ``Chembl.target``.
    """

    def filter(self, **kwargs) -> Sequence[NestedDotDict]:
        raise NotImplementedError()

    def get(self, arg) -> Optional[NestedDotDict]:
        raise NotImplementedError()

    @classmethod
    def wrap(cls, obj) -> ChemblEntrypoint:
        """

        Args:
            obj:

        Returns:

        """

        class X(ChemblEntrypoint):
            def filter(self, **kwargs) -> Sequence[NestedDotDict]:
                return getattr(obj, "filter")(**kwargs)

            def get(self, arg) -> Optional[NestedDotDict]:
                return getattr(obj, "get")(arg)

        return X()


class ChemblApi(metaclass=abc.ABCMeta):
    """
    Wraps the whole ChEMBL API.
    """

    def __getattribute__(self, item: str) -> ChemblEntrypoint:
        raise NotImplementedError()

    @classmethod
    def wrap(cls, obj) -> ChemblApi:
        """

        Args:
            obj:

        Returns:

        """

        class X(ChemblApi):
            def __getattribute__(self, item: str) -> ChemblEntrypoint:
                return ChemblEntrypoint.wrap(getattr(obj, item))

        return X()


@dataclass(frozen=True, order=True, repr=True)
class AbstractHit:
    record_id: int
    compound_id: int
    inchikey: str
    compound_lookup: str
    compound_name: str

    @property
    def predicate(self) -> str:
        raise NotImplementedError()

    def __hash__(self):
        return hash(self.record_id)

    @classmethod
    def fields(cls) -> Sequence[str]:
        return [f.name for f in dataclasses.fields(cls)]


H = TypeVar("H", bound=AbstractHit, covariant=True)


class Search(Generic[H], metaclass=abc.ABCMeta):
    """"""

    def __init__(self, api: ChemblApi, tax: Taxonomy):
        self.api = api
        self.tax = tax

    def find_all(self, compounds: Sequence[str]) -> Sequence[H]:
        lst = []
        for compound in compounds:
            lst.extend(self.find(compound))
        return lst

    def find(self, compound: str) -> Sequence[H]:
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
