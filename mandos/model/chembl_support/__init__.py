from __future__ import annotations
import enum
from dataclasses import dataclass
from typing import Set, Union

from mandos.model import CleverEnum, CompoundNotFoundError


class ChemblCompoundLookupError(CompoundNotFoundError):
    """"""


class ActivityRelation(CleverEnum):
    lt = enum.auto()
    gt = enum.auto()
    le = enum.auto()
    ge = enum.auto()
    eq = enum.auto()
    approx = enum.auto()

    @classmethod
    def of(cls, name: Union[int, str]) -> CleverEnum:
        return super().of(
            {
                "<": "lt",
                ">": "gt",
                "=": "eq",
                "~": "approx",
                "<=": "le",
                ">=": "ge",
            }.get(name, name)
        )


class DataValidityComment(CleverEnum):
    potential_missing_data = enum.auto()
    potential_author_error = enum.auto()
    manually_validated = enum.auto()
    outside_typical_range = enum.auto()
    non_standard_unit_for_type = enum.auto()
    author_confirmed_error = enum.auto()

    @classmethod
    def resolve(cls, st: str) -> Set[DataValidityComment]:
        found = set()
        for s in st.lower().split(","):
            s = s.strip()
            if s == "@all":
                return set(cls)
            if s == "@negative":
                match = DataValidityComment.negative_comments()
            elif s == "@positive":
                match = DataValidityComment.positive_comments()
            else:
                match = {DataValidityComment.of(s)}
            for m in match:
                found.add(m)
        return found

    @property
    def is_positive(self) -> bool:
        return self in DataValidityComment.positive_comments()

    @property
    def is_negative(self) -> bool:
        return self in DataValidityComment.negative_comments()

    @classmethod
    def positive_comments(cls) -> Set[DataValidityComment]:
        return {DataValidityComment.manually_validated}

    @classmethod
    def negative_comments(cls) -> Set[DataValidityComment]:
        return {
            DataValidityComment.potential_missing_data,
            DataValidityComment.potential_author_error,
            DataValidityComment.outside_typical_range,
            DataValidityComment.non_standard_unit_for_type,
            DataValidityComment.author_confirmed_error,
        }


@dataclass(frozen=True, order=True, repr=True)
class ChemblCompound:
    """"""

    chid: str
    inchikey: str
    name: str


__all__ = ["ChemblCompound", "ChemblCompoundLookupError", "DataValidityComment", "ActivityRelation"]
