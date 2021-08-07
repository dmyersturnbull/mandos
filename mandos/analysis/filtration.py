"""
Tool to filter annotations.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Optional, Sequence, Set, Union

import regex
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.hits import AbstractHit, HitFrame
from mandos.model.utils.hit_utils import HitUtils

_Type = Union[str, int, float, datetime]


class Operator(enum.Enum):
    """"""

    eq = enum.auto()
    ne = enum.auto()
    lt = enum.auto()
    gt = enum.auto()
    le = enum.auto()
    ge = enum.auto()
    like = enum.auto()
    is_in = enum.auto()
    not_in = enum.auto()

    @classmethod
    def parse(cls, s: str):
        if isinstance(s, Operator):
            return s
        if s in cls:
            return cls[s]
        return cls.rev_symbols().get(s)

    @property
    def symbol(self) -> str:
        return dict(
            eq="=", ne="!=", lt="<", gt=">", le="<=", ge=">=", like="$", is_in="<<", not_in="!<<"
        )[self.name]

    @classmethod
    def rev_symbols(cls) -> Mapping[str, Operator]:
        return {e.symbol: e for e in cls}


@dataclass(frozen=True, repr=True)
class Expression:
    """"""

    op: Operator
    val: _Type
    extra: Optional[Set[_Type]]

    def matches(self, value: _Type) -> bool:
        if type(value) != type(self.val):
            raise TypeError(f"{type(value)} != {type(self.val)}")
        if self.op is Operator.like:
            return regex.compile(self.val, flags=regex.V1).fullmatch(str(value)) is not None
        if self.op is Operator.is_in:
            return value in self.extra
        if self.op is Operator.not_in:
            return value not in self.extra
        call = f"__{self.op}__"
        return getattr(value, call) != getattr(self.val, call)

    @classmethod
    def parse(cls, s: str, context: NestedDotDict) -> Expression:
        op = Operator.parse(s)
        if op is None:
            op = Operator.eq
        val = s[len(op.symbol) :]
        return Expression(op, val, set(context.get(val, [])))


class Filtration:
    def __init__(self, key_to_statements: Mapping[str, Mapping[str, Sequence[Expression]]]):
        self._x = key_to_statements

    @classmethod
    def from_file(cls, path: Path) -> Filtration:
        dot = NestedDotDict.read_toml(path)
        return cls.from_toml(dot)

    @classmethod
    def from_toml(cls, dot: NestedDotDict) -> Filtration:
        data = dot.get("mandos.filter", [])
        return Filtration({d["key"]: {k: v for k, v in d.items() if k != "key"} for d in data})

    def apply(self, df: HitFrame) -> HitFrame:
        hits = [h for h in df.to_hits() if self.keep(h)]
        return HitUtils.hits_to_df(hits)

    def keep(self, hit: AbstractHit) -> bool:
        if hit.search_key not in self._x:
            return True
        for field, values in self._x[hit.search_key].items():
            if not hasattr(hit, field):
                raise ValueError(f"No field {field} in {hit.__class__.__name__}")
            if not self._matches(getattr(hit, field), field):
                return False
        return True

    def _matches(self, actual: _Type, allowed: Sequence[Expression]) -> bool:
        for e in allowed:
            if e.matches(actual):
                return True


__all__ = ["Filtration"]
