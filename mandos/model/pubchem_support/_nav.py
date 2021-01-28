from __future__ import annotations
from dataclasses import dataclass
from typing import (
    List,
    Union,
    Sequence,
    Callable,
    Set,
    FrozenSet,
    Any,
    Optional,
    Type,
    TypeVar,
    Iterable,
)

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.base_tools import BaseTools

from mandos.model.pubchem_support._nav_model import FilterFn


T = TypeVar("T", covariant=True)
V = TypeVar("V", covariant=True)

catchable_errors = (KeyError, ValueError, LookupError, TypeError)


class NavError(Exception):
    pass


class MapError(NavError):
    pass


class FlatmapError(NavError):
    pass


class FilterError(NavError):
    pass


def _identity(x: T) -> T:
    return x


# This happens to be duplicated in nav_utils,
# but I *really* don't want that dependency
def _request_only(things: Iterable[str]) -> Optional[str]:
    # TODO: Did I mean to excludeNone here?
    things = [s.strip() for s in things if s is not None]
    if len(things) > 1:
        raise ValueError(f"{len(things)} items in {things}")
    elif len(things) == 0:
        return None
    else:
        return things[0]


def _get_conversion_fn(fn: Union[None, str, Callable[[Any], Any]]) -> Callable[[Any], Any]:
    if fn is None:
        return _identity
    if isinstance(fn, str):
        return _request_only
    else:
        return fn


@dataclass(frozen=True, eq=True)
class AbstractJsonNavigator:
    """"""


@dataclass(frozen=True, eq=True)
class JsonNavigator(AbstractJsonNavigator):
    contents: List[NestedDotDict]

    @classmethod
    def create(
        cls, dct: Union[dict, NestedDotDict, Sequence[dict], Sequence[NestedDotDict]]
    ) -> JsonNavigator:
        if hasattr(dct, "items"):
            dct = [dct]
        return JsonNavigator([NestedDotDict(dict(**d, _landmark="")) for d in dct])

    @property
    def get(self) -> List[NestedDotDict]:
        return self.contents

    def __truediv__(
        self, key: Union[int, str, FilterFn, Callable[[NestedDotDict], NestedDotDict]]
    ) -> JsonNavigator:
        if isinstance(key, FilterFn):
            try:
                return self._filter(key)
            except catchable_errors as e:
                raise FilterError(f"Failed to go filter navigator with '{key}': {e}")
        else:
            try:
                return self._go_inside(key)
            except catchable_errors as e:
                raise MapError(f"Failed to map navigator with '{key}': {e}")

    def __mod__(self, key: Union[int, str]) -> JsonNavigator:
        new = {}
        for z in self.contents:
            if z[key] in new:
                raise ValueError(f"{key} found twice")
            new[z[key]] = z
        return JsonNavigator([NestedDotDict(new)])

    def __floordiv__(self, keys: Sequence[str]) -> JsonNavigatorListOfLists:
        try:
            return JsonNavigatorListOfLists([[z.get(key) for key in keys] for z in self.contents])
        except catchable_errors as e:
            raise FlatmapError(f"Failed to flatmap from navigator with '{keys}': {e}")

    def __rshift__(self, key: str) -> JsonNavigatorListOfOptionals:
        try:
            return JsonNavigatorListOfOptionals([z.get(key) for z in self.contents])
        except catchable_errors as e:
            raise FlatmapError(f"Failed to 'double-flatmap' from navigator with '{key}': {e}")

    def _filter(self, keep_where: FilterFn) -> JsonNavigator:
        if callable(keep_where):
            return JsonNavigator([z for z in self.contents if keep_where(z)])
        else:
            key, values = keep_where
            if not isinstance(values, (Set, FrozenSet, List)):
                values = {values}
            return JsonNavigator([z for z in self.contents if z.get(key) in values])

    def _go_inside(self, key: Union[int, str]) -> JsonNavigator:
        new = []
        for z in self.contents:
            if key in z:
                # nav = z.get_as("_nav", list, [])
                # nav.append(z[key])
                if isinstance(z.get(key), list):
                    new.extend([NestedDotDict(dict(**m)) for m in z[key]])
                elif isinstance(z.get(key), NestedDotDict):
                    new.append(NestedDotDict(dict(**z[key])))
                elif isinstance(z.get(key), dict):
                    new.append(NestedDotDict(dict(**z[key])))
                else:
                    raise ValueError(f"{key} value is {type(z[key])}: {z[key]}")
        return JsonNavigator(new)


@dataclass(frozen=True, eq=True)
class JsonNavigatorListOfLists(AbstractJsonNavigator):
    contents: List[List[Any]]

    def __truediv__(
        self,
        keys: Union[
            Sequence[Union[None, str, Callable[[Any], Any]]], FilterFn, Callable[[List[T]], Any]
        ],
    ) -> JsonNavigatorListOfLists:
        if isinstance(keys, FilterFn):
            try:
                return self._filter(keys)
            except catchable_errors as e:
                raise FilterError(f"Failed to filter list-of-lists with '{keys}': {e}")
        else:
            try:
                return self._go_inside(keys)
            except catchable_errors as e:
                raise MapError(f"Failed to map list-of-lists with '{keys}': {e}")

    def __rshift__(self, conversion: Callable[[List[List[T]]], Any]) -> JsonNavigatorSingleOptional:
        try:
            return JsonNavigatorSingleOptional(conversion(self.contents))
        except catchable_errors as e:
            raise FlatmapError(
                f"Failed to 'double-flatmap' from list-of-lists with '{conversion}': {e}"
            )

    def __floordiv__(self, conversion: Callable[[List[T]], Any]) -> JsonNavigatorListOfOptionals:
        try:
            return JsonNavigatorListOfOptionals([conversion(z) for z in self.contents])
        except catchable_errors as e:
            raise FlatmapError(f"Failed to flatmap from list-of-lists with '{conversion}': {e}")

    def _filter(self, keep_if: FilterFn) -> JsonNavigatorListOfLists:
        return JsonNavigatorListOfLists([z for z in self.contents if keep_if(z)])

    def _go_inside(
        self, keys: Sequence[Union[None, str, Callable[[Any], Any]]]
    ) -> JsonNavigatorListOfLists:
        fns = [_get_conversion_fn(fn) for fn in keys]
        return JsonNavigatorListOfLists(
            [
                [fn(value) for value, fn in BaseTools.zip_list(contents, fns)]
                for contents in self.contents
            ]
        )


@dataclass(frozen=True, eq=True)
class JsonNavigatorListOfOptionals(AbstractJsonNavigator):
    contents: List[Optional[T]]

    @property
    def to_list(self) -> List[T]:
        return [k for k in self.contents if k is not None]

    @property
    def to_set(self) -> FrozenSet[T]:
        return frozenset([k for k in self.contents if k is not None])

    def __truediv__(
        self, key: Union[None, str, FilterFn, Callable[[Any], Any]]
    ) -> JsonNavigatorListOfOptionals:
        if isinstance(key, FilterFn):
            try:
                return self._filter(key)
            except catchable_errors as e:
                raise FilterError(f"Failed to filter list-of-optionals with '{key}': {e}")
        else:
            try:
                return self._go_inside(key)
            except (KeyError, ValueError, LookupError) as e:
                raise FlatmapError(f"Failed to map list-of-optionals with '{key}': {e}")

    def __rshift__(self, key: Callable[[List[Optional[Any]]], Any]) -> JsonNavigatorSingleOptional:
        # we can't skip 2
        return self // key

    def __floordiv__(
        self, key: Callable[[List[Optional[Any]]], Any]
    ) -> JsonNavigatorSingleOptional:
        try:
            return JsonNavigatorSingleOptional(key(self.contents))
        except catchable_errors as e:
            raise FlatmapError(f"Failed to flatmap from list-of-optionals with '{key}': {e}")

    def _go_inside(
        self, key: Union[None, str, Callable[[Any], Any]]
    ) -> JsonNavigatorListOfOptionals:
        fn = _get_conversion_fn(key)
        return JsonNavigatorListOfOptionals(
            [None if content is None else fn(content) for content in self.contents]
        )

    def _filter(
        self, keep_if: Union[Callable[[Optional[T]], bool]]
    ) -> JsonNavigatorListOfOptionals:
        return JsonNavigatorListOfOptionals([z for z in self.contents if keep_if(z)])


@dataclass(frozen=True, eq=True)
class JsonNavigatorSingleOptional(AbstractJsonNavigator):
    contents: Optional[T]

    @property
    def get(self) -> T:
        return self.contents

    def __floordiv__(
        self, conversion: Union[Type[T], Callable[[T], V]]
    ) -> JsonNavigatorSingleOptional:
        try:
            return JsonNavigatorSingleOptional(conversion(self.contents))
        except catchable_errors as e:
            raise FlatmapError(f"Failed to map single-optional with '{conversion}': {e}")


__all__ = [
    "JsonNavigator",
    "JsonNavigatorListOfLists",
    "JsonNavigatorListOfOptionals",
    "AbstractJsonNavigator",
    "JsonNavigatorSingleOptional",
    "NavError",
    "MapError",
    "FlatmapError",
    "FilterError",
]
