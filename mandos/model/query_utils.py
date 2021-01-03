"""
Support classes to help with querying and processing web data.
"""
from __future__ import annotations

import logging
import json
import re
import time
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Sequence,
    Set,
    List,
    Union,
    Optional,
    Type,
    TypeVar,
    Iterable,
    FrozenSet,
)

import requests
import numpy as np
from pocketutils.core.chars import Chars
from pocketutils.tools.base_tools import BaseTools
from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger("mandos")


@dataclass(frozen=True)
class FilterFn:
    keep_if: Callable[[Any], bool]

    def __call__(self, *args, **kwargs):
        return self.keep_if(*args, **kwargs)


class Fns:
    @classmethod
    def has_key(cls, key: str) -> FilterFn:
        return FilterFn(lambda content: key in content)

    @classmethod
    def key_does_not_equal(cls, key: str, disallowed_value: Any) -> FilterFn:
        return FilterFn(lambda content: content.get(key) != disallowed_value)

    @classmethod
    def key_equals(cls, key: str, allowed_value: Any) -> FilterFn:
        return FilterFn(lambda content: content.get(key) == allowed_value)

    @classmethod
    def key_is_not_in(cls, key: str, disallowed_values: Set[Any]) -> FilterFn:
        return FilterFn(lambda content: content.get(key) not in disallowed_values)

    @classmethod
    def key_is_in(cls, key: str, allowed_values: Set[Any]) -> FilterFn:
        return FilterFn(lambda content: content.get(key) in allowed_values)

    @classmethod
    def construct(cls, tp: Type[T]) -> Callable[[Iterable[Any]], T]:
        """
        Function that constructs an instance whose attributes are from the passed list.
        """

        def construct(things: Iterable[str]) -> Optional[str]:
            x = list(things)
            return tp(*x)

        return construct

    @classmethod
    def join_nonnulls(cls) -> Callable[[Iterable[str]], Optional[str]]:
        def opt_join(things: Iterable[str]) -> Optional[str]:
            x = list(things)
            return None if len(x) == 0 else ";".join(x)

        return opt_join

    @classmethod
    def split_and_flatten_nonnulls(
        cls, sep: str, skip_nulls: bool = False
    ) -> Callable[[Iterable[str]], Set[str]]:
        def split_flat(things: Iterable[str]) -> Set[str]:
            results = set()
            for thing in things:
                if thing is not None or not skip_nulls:
                    # let it fail if skip_nulls is False
                    for bit in thing.split(sep):
                        results.add(bit)
            return results

        return split_flat

    @classmethod
    def request_only(cls) -> Callable[[Iterable[str]], Optional[str]]:
        def only_nonreq(things: Iterable[str]) -> Optional[str]:
            things = list(things)
            if len(things) > 1:
                raise ValueError(f"{len(things)} items in {things}")
            elif len(things) == 0:
                return None
            else:
                return things[0]

        return only_nonreq

    @classmethod
    def roman_to_arabic(
        cls, min_val: Optional[int] = None, max_val: Optional[int] = None
    ) -> Callable[[str], int]:
        def roman_to_arabic(s: str) -> int:
            mp = dict(I=1, V=5, X=10, L=50, C=100, D=500, M=1000)
            coeff = 1
            if s.startswith("-") or s.startswith(Chars.minus):
                coeff = -1
                s = s[1:]
            v = sum((mp[c] for c in s))
            if min_val is not None and v < min_val or min_val is not None and v > max_val:
                raise ValueError(f"Value {s} (int={v}) is out of range ({min_val}, {max_val})")
            return coeff * v

        return roman_to_arabic

    @classmethod
    def require_only(cls) -> Callable[[Iterable[str]], Optional[str]]:
        return BaseTools.only

    @classmethod
    def extract_group_1(
        cls, pattern: Union[str, re.Pattern]
    ) -> Callable[[Optional[Any]], Optional[str]]:
        pattern = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)

        def _match(thing: Optional[str]) -> Optional[str]:
            if thing is None:
                return None
            match = pattern.fullmatch(str(thing))
            if match is None:
                return None
            return match.group(1)

        return _match

    @classmethod
    def lowercase_unless_acronym(cls) -> Callable[[str], str]:
        def lowercase_unless_acronym(s: str) -> str:
            return s if s.isupper() else s.lower()

        return lowercase_unless_acronym

    @classmethod
    def split_bars(cls, sep: str = "||") -> Callable[[Sequence[str]], str]:
        return lambda value: value.split(sep)

    @staticmethod
    def n_bar_items(sep: str = "||") -> Callable[[Sequence[str]], int]:
        return lambda value: len(set(value.split(sep)))

    @staticmethod
    def not_null(value):
        return value is not None

    @staticmethod
    def identity(value):
        return value

    @staticmethod
    def req_is_str(value):
        if not isinstance(value, str):
            raise ValueError(f"{value} is a {type(value)}, not str")
        return value

    @staticmethod
    def req_is_int(value):
        if not isinstance(value, int):
            raise ValueError(f"{value} is a {type(value)}, not int")
        return value


def _get_conversion_fn(fn: Union[None, str, Callable[[Any], Any]]) -> Callable[[Any], Any]:
    if fn is None:
        return Fns.identity
    if isinstance(fn, str):
        return Fns.request_only()
    else:
        return fn


T = TypeVar("T", covariant=True)
V = TypeVar("V", covariant=True)


@dataclass(frozen=True, eq=True)
class AbstractJsonNavigator:
    """"""


@dataclass(frozen=True, eq=True)
class JsonNavigatorSingleOptional(AbstractJsonNavigator):
    contents: Optional[T]

    @property
    def get(self) -> T:
        return self.contents

    def __floordiv__(
        self, conversion: Union[Type[T], Callable[[T], V]]
    ) -> JsonNavigatorSingleOptional:
        return JsonNavigatorSingleOptional(conversion(self.contents))


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
            return self._filter(key)
        else:
            return self._go_inside(key)

    def __rshift__(self, key: Callable[[List[Optional[Any]]], Any]) -> JsonNavigatorSingleOptional:
        # we can't skip 2
        return self // key

    def __floordiv__(
        self, key: Callable[[List[Optional[Any]]], Any]
    ) -> JsonNavigatorSingleOptional:
        return JsonNavigatorSingleOptional(key(self.contents))

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
class JsonNavigatorListOfLists(AbstractJsonNavigator):
    contents: List[List[Any]]

    def __truediv__(
        self,
        keys: Union[
            Sequence[Union[None, str, Callable[[Any], Any]]], FilterFn, Callable[[List[T]], Any]
        ],
    ) -> JsonNavigatorListOfLists:
        if isinstance(keys, FilterFn):
            return self._filter(keys)
        else:
            return self._go_inside(keys)

    def __rshift__(self, conversion: Callable[[List[List[T]]], Any]) -> JsonNavigatorSingleOptional:
        return JsonNavigatorSingleOptional(conversion(self.contents))

    def __floordiv__(self, conversion: Callable[[List[T]], Any]) -> JsonNavigatorListOfOptionals:
        return JsonNavigatorListOfOptionals([conversion(z) for z in self.contents])

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

    def _filter(self, keep_if: FilterFn) -> JsonNavigatorListOfLists:
        return JsonNavigatorListOfLists([z for z in self.contents if keep_if(z)])


@dataclass(frozen=True, eq=True)
class JsonNavigator(AbstractJsonNavigator):
    contents: List[NestedDotDict]

    @property
    def get(self) -> List[NestedDotDict]:
        return self.contents

    @classmethod
    def create(
        cls, dct: Union[dict, NestedDotDict, Sequence[dict], Sequence[NestedDotDict]]
    ) -> JsonNavigator:
        if hasattr(dct, "items"):
            dct = [dct]
        return JsonNavigator([NestedDotDict(dict(**d, _landmark="")) for d in dct])

    def __truediv__(
        self, key: Union[int, str, FilterFn, Callable[[NestedDotDict], NestedDotDict]]
    ) -> JsonNavigator:
        if isinstance(key, FilterFn):
            return self._filter(key)
        else:
            return self._go_inside(key)

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

    def _filter(self, keep_where: FilterFn) -> JsonNavigator:
        if callable(keep_where):
            return JsonNavigator([z for z in self.contents if keep_where(z)])
        else:
            key, values = keep_where
            if not isinstance(values, (Set, FrozenSet, List)):
                values = {values}
            return JsonNavigator([z for z in self.contents if z.get(key) in values])

    def __mod__(self, key: Union[int, str]) -> JsonNavigator:
        new = {}
        for z in self.contents:
            if z[key] in new:
                raise ValueError(f"{key} found twice")
            new[z[key]] = z
        return JsonNavigator([NestedDotDict(new)])

    def __floordiv__(self, keys: Sequence[str]) -> JsonNavigatorListOfLists:
        return JsonNavigatorListOfLists([[z.get(key) for key in keys] for z in self.contents])

    def __rshift__(self, key: str) -> JsonNavigatorListOfOptionals:
        return JsonNavigatorListOfOptionals([z.get(key) for z in self.contents])


class QueryExecutor:
    def __init__(
        self,
        sec_delay_min: float = 0.25,
        sec_delay_max: float = 0.25,
        encoding: Optional[str] = "utf-8",
    ):
        self._min = sec_delay_min
        self._max = sec_delay_max
        self._rand = np.random.RandomState()
        self._encoding = encoding
        self._next_at = 0

    def __call__(
        self, url: str, method: str = "get", encoding: Optional[str] = "-1", errors: str = "ignore"
    ) -> str:
        encoding = self._encoding if encoding == "-1" else encoding
        now = time.monotonic()
        if now < self._next_at:
            time.sleep(self._next_at - now)
        content = getattr(requests, method)(url).content
        if encoding is None:
            data = content.decode(errors=errors)
        else:
            data = content.decode(encoding=encoding, errors=errors)
        self._next_at = time.monotonic() + self._rand.uniform(self._min + 0.0001, self._max)
        return data


__all__ = ["JsonNavigator", "QueryExecutor", "JsonNavigatorListOfLists", "Fns", "FilterFn"]
