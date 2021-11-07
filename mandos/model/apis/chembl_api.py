"""
An abstraction for the ChEMBL REST API.
Designed to facilitate testing, but also improves static type checking.
"""
from __future__ import annotations

import abc
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

import decorateme
from pocketutils.core.dot_dict import NestedDotDict


@decorateme.auto_repr_str()
class ChemblFilterQuery(metaclass=abc.ABCMeta):
    """
    Wraps the result of calling ``filter`` on a ChEMBL query.
    Supports iterating over results (``__iter__`), getting a single item (``__getitem__`),
    and calling ``only(lst)``.
    """

    def only(self, items: Sequence[str]) -> ChemblFilterQuery:
        """
        Turns this into a query for a single record.
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
        Mocks.
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
        Wraps.
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


@decorateme.auto_repr_str()
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
        Wraps.
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
    def protein_class(self) -> ChemblEntrypoint:
        return self.__dict__["protein_class"]

    @property
    def target_component(self) -> ChemblEntrypoint:
        return self.__dict__["target_component"]

    @property
    def target_prediction(self) -> ChemblEntrypoint:
        return self.__dict__["target_prediction"]

    def __getattribute__(self, item: str) -> ChemblEntrypoint:
        raise NotImplementedError()

    @classmethod
    def mock(cls, entrypoints: Mapping[str, ChemblEntrypoint]) -> ChemblApi:
        @decorateme.auto_repr_str()
        class X(ChemblApi):
            def __getattribute__(self, item: str) -> ChemblEntrypoint:
                return entrypoints[item]

        X.__name__ = f"MockedChemblApi({entrypoints})"
        return X()

    @classmethod
    def wrap(cls, obj) -> ChemblApi:
        class X(ChemblApi):
            def __getattribute__(self, item: str) -> ChemblEntrypoint:
                return ChemblEntrypoint.wrap(getattr(obj, item))

            def __repr__(self):
                return f"ChemblApi(Wrapped: {obj})"

            def __str__(self):
                return repr(self)

        return X()


__all__ = [
    "ChemblApi",
    "ChemblEntrypoint",
    "ChemblFilterQuery",
]
