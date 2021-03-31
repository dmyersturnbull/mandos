"""
Support classes to help with querying and processing web data.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import (
    Any,
    Callable,
    Set,
    Union,
    Optional,
    Type,
    TypeVar,
    Iterable,
    FrozenSet,
)

from pocketutils.tools.base_tools import BaseTools
from pocketutils.tools.string_tools import StringTools

from mandos import logger
from mandos.model.pubchem_support._nav_model import FilterFn

T = TypeVar("T")

empty_frozenset = frozenset([])


class Filter:
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


class Flatmap:
    @classmethod
    def construct(cls, tp: Type[T]) -> Callable[[Iterable[Any]], T]:
        """
        Function that constructs an instance whose attributes are from the passed list.
        """

        def construct(things: Iterable[str]) -> Optional[str]:
            return tp(*things)

        return construct

    @classmethod
    def join_nonnulls(cls, sep: str = "; ") -> Callable[[Iterable[str]], Optional[str]]:
        def opt_join(things: Iterable[str]) -> Optional[str]:
            x = [s.strip() for s in things]
            return None if len(x) == 0 else sep.join(x)

        return opt_join

    @classmethod
    def request_only(cls) -> Callable[[Iterable[str]], Optional[str]]:
        def only_nonreq(things: Iterable[str]) -> Optional[str]:
            # TODO: Did I mean to excludeNone here?
            things = [s.strip() for s in things if s is not None]
            if len(things) > 1:
                raise ValueError(f"{len(things)} items in {things}")
            elif len(things) == 0:
                return None
            else:
                return things[0]

        return only_nonreq

    @classmethod
    def require_only(cls) -> Callable[[Iterable[str]], Optional[str]]:
        return BaseTools.only


class Mapx:
    @classmethod
    def roman_to_arabic(
        cls, min_val: Optional[int] = None, max_val: Optional[int] = None
    ) -> Callable[[str], int]:
        def roman_to_arabic(s: str) -> int:
            return StringTools.roman_to_arabic(s.strip(), min_val=min_val, max_val=max_val)

        return roman_to_arabic

    @classmethod
    def split_and_flatten_nonnulls(
        cls, sep: str, skip_nulls: bool = False
    ) -> Callable[[Iterable[Union[str, int, float, None]]], Set[str]]:
        def split_flat(things: Iterable[str]) -> Set[str]:
            results = set()
            for thing in things:
                if thing is not None and thing != float("NaN") or not skip_nulls:
                    # let it fail if skip_nulls is False
                    for bit in str(thing).split(sep):
                        results.add(bit.strip())
            return results

        return split_flat

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
            s = s.strip()
            return s if s.isupper() else s.lower()

        return lowercase_unless_acronym

    @classmethod
    def n_bar_items(cls, sep: str = "||") -> Callable[[Optional[str]], int]:
        def n_bar_items(value: str) -> int:
            return len(value.split(sep))

        return n_bar_items

    @classmethod
    def not_null(cls) -> Callable[[Any], bool]:
        return lambda value: value is not None

    @classmethod
    def identity(cls) -> Callable[[T], T]:
        return lambda value: value

    @classmethod
    def int_date(cls, nullable: bool = False) -> Callable[[Optional[str]], Optional[date]]:
        def int_date(s: Optional[str]) -> Optional[date]:
            if s is None and nullable:
                return None
            return datetime.strptime(str(s).strip(), "%Y%m%d").date()

        return int_date

    @classmethod
    def get_int(cls, nullable: bool = False) -> Callable[[str], Optional[int]]:
        def get_int(value):
            if nullable and value is None:
                return None
            elif not isinstance(value, (int, float, str)):
                raise TypeError(f"{value} is a {type(value)}, not int-like")
            return int(value)

        return get_int

    @classmethod
    def req_is(cls, type_, nullable: bool = False, then_convert=None) -> Callable[[str], str]:
        def req_is(value):
            if nullable and value is None:
                pass
            elif not isinstance(value, type_):
                raise TypeError(f"{value} is a {type(value)}, not {type_}")
            return value if then_convert is None else then_convert(value)

        req_is.__name__ = f"req_is_{type_}" + ("_or_null" if nullable else "")
        return req_is

    @classmethod
    def str_to(
        cls, type_: Callable[[str], T], nullable: bool = False, flex_type: bool = False
    ) -> Callable[[str], str]:
        def str_to(value: Optional[str]) -> Optional[T]:
            if type_ is not None and not flex_type and not isinstance(value, str):
                raise TypeError(f"{value} is a {type(value)}, not str")
            if not nullable and value is None:
                raise ValueError(f"Value for type {type_} is None")
            elif value is None:
                return None
            return type_(str(value).strip())

        str_to.__name__ = f"req_is_{type_}" + ("_or_null" if nullable else "")
        return str_to

    @classmethod
    def split_to(
        cls, type_, sep: str = "||", nullable: bool = False
    ) -> Callable[[Optional[str]], FrozenSet[int]]:
        def split_to(value: str) -> FrozenSet[int]:
            return frozenset([type_(x) for x in cls.split(sep, nullable=nullable)(value)])

        return split_to

    @classmethod
    def split(cls, sep: str, nullable: bool = False) -> Callable[[Optional[str]], FrozenSet[str]]:
        def split(value: str) -> FrozenSet[str]:
            if value is None and not nullable:
                raise ValueError(f"Value is None")
            if value is None:
                return empty_frozenset
            return frozenset([s.strip() for s in str(value).split(sep)])

        return split


__all__ = ["Filter", "Mapx", "Flatmap"]
