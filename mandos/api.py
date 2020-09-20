"""
An abstraction for the ChEMBL REST API.
Designed to facilitate testing, but also improves static type checking.
"""
from __future__ import annotations

import abc
import logging
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger("mandos")


class ChemblFilterQuery(metaclass=abc.ABCMeta):
    """
    Wraps the result of calling ``filter`` on a ChEMBL query.
    Supports iterating over results (``__iter__`), getting a single item (``__getitem__`), and calling ``only(lst)``.
    """

    def only(self, items: Sequence[str]) -> ChemblFilterQuery:
        """

        Args:
            items:

        Returns:

        """
        raise NotImplementedError()

    def __getitem__(self, item: int) -> NestedDotDict:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[NestedDotDict]:
        raise NotImplementedError()

    @classmethod
    def mock(cls, items: Sequence[dict]):
        """

        Args:
            items:

        Returns:

        """

        class F(ChemblFilterQuery):
            def only(self, _: Sequence[str]) -> ChemblFilterQuery:
                return self

            def __getitem__(self, item: int) -> NestedDotDict:
                return NestedDotDict(items[item])

            def __len__(self) -> int:
                return len(items)

            def __iter__(self) -> Iterator[NestedDotDict]:
                return iter([NestedDotDict(x) for x in items])

        return F()

    @classmethod
    def wrap(cls, query):
        """

        Args:
            query:

        Returns:

        """

        class F(ChemblFilterQuery):
            def only(self, items: Sequence[str]) -> ChemblFilterQuery:
                # TODO technically not returning this
                return getattr(query, "only")(items)

            def __getitem__(self, item: int) -> NestedDotDict:
                return NestedDotDict(query[item])

            def __len__(self) -> int:
                return len(query)

            def __iter__(self) -> Iterator[NestedDotDict]:
                return iter([NestedDotDict(x) for x in query])

        return F()


class ChemblEntrypoint:
    """
    Wraps just part of a node in the ChEMBL REST API.
    Ex ``Chembl.target``.
    """

    def filter(self, **kwargs) -> ChemblFilterQuery:
        raise NotImplementedError()

    def get(self, arg: str) -> Optional[NestedDotDict]:
        raise NotImplementedError()

    @classmethod
    def mock(
        cls,
        get_items: Mapping[str, dict],
        filter_items: Optional[Callable[[Mapping[str, Any]], Sequence[dict]]] = None,
    ) -> ChemblEntrypoint:
        """

        Args:
            get_items: Map from single arg for calling ``get`` to the item to return
            filter_items: Map from kwarg-set for calling ``filter`` to the list of items to return;
                          If None, returns ``items`` in all cases

        Returns:

        """

        class X(ChemblEntrypoint):
            def filter(self, **kwargs) -> ChemblFilterQuery:
                if filter_items is None:
                    return ChemblFilterQuery.mock(list(get_items.values()))
                items = filter_items(kwargs)
                return ChemblFilterQuery.mock(items)

            def get(self, arg: str) -> Optional[NestedDotDict]:
                return NestedDotDict(get_items[arg])

        return X()

    @classmethod
    def wrap(cls, obj) -> ChemblEntrypoint:
        """

        Args:
            obj:

        Returns:

        """

        class X(ChemblEntrypoint):
            def filter(self, **kwargs) -> ChemblFilterQuery:
                query = getattr(obj, "filter")(**kwargs)
                return ChemblFilterQuery.wrap(query)

            def get(self, arg: str) -> Optional[NestedDotDict]:
                return NestedDotDict(getattr(obj, "get")(arg))

        return X()


class ChemblApi(metaclass=abc.ABCMeta):
    """
    Wraps the whole ChEMBL API.
    """

    @property
    def activity(self) -> ChemblEntrypoint:
        return self.__dict__["activity"]

    @property
    def assay(self) -> ChemblEntrypoint:
        return self.__dict__["assay"]

    @property
    def atc_class(self) -> ChemblEntrypoint:
        return self.__dict__["atc_class"]

    @property
    def drug(self) -> ChemblEntrypoint:
        return self.__dict__["drug"]

    @property
    def drug_indication(self) -> ChemblEntrypoint:
        return self.__dict__["drug_indication"]

    @property
    def mechanism(self) -> ChemblEntrypoint:
        return self.__dict__["mechanism"]

    @property
    def molecule(self) -> ChemblEntrypoint:
        return self.__dict__["molecule"]

    @property
    def molecule_form(self) -> ChemblEntrypoint:
        return self.__dict__["molecule_form"]

    @property
    def organism(self) -> ChemblEntrypoint:
        return self.__dict__["mechanism"]

    @property
    def go_slim(self) -> ChemblEntrypoint:
        return self.__dict__["go_slim"]

    @property
    def target(self) -> ChemblEntrypoint:
        return self.__dict__["target"]

    @property
    def target_relation(self) -> ChemblEntrypoint:
        return self.__dict__["target_relation"]

    @property
    def target_prediction(self) -> ChemblEntrypoint:
        return self.__dict__["target_prediction"]

    def __getattribute__(self, item: str) -> ChemblEntrypoint:
        raise NotImplementedError()

    @classmethod
    def mock(cls, entrypoints: Mapping[str, ChemblEntrypoint]) -> ChemblApi:
        """

        Args:
            entrypoints:

        Returns:

        """

        class X(ChemblApi):
            def __getattribute__(self, item: str) -> ChemblEntrypoint:
                return entrypoints[item]

        return X()

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


__all__ = ["ChemblApi", "ChemblEntrypoint", "ChemblFilterQuery"]
