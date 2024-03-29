from __future__ import annotations

import enum
from typing import Set, Union

from pocketutils.core.enums import CleverEnum


class ActivityRelation(CleverEnum):
    lt = ()
    gt = ()
    le = ()
    ge = ()
    eq = ()
    approx = ()

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
    potential_missing_data = ()
    potential_transcription_error = ()
    potential_author_error = ()
    manually_validated = ()
    outside_typical_range = ()
    non_standard_unit_for_type = ()
    author_confirmed_error = ()

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
            DataValidityComment.potential_transcription_error,
            DataValidityComment.potential_author_error,
            DataValidityComment.outside_typical_range,
            DataValidityComment.non_standard_unit_for_type,
            DataValidityComment.author_confirmed_error,
        }


class AssayType(CleverEnum):
    binding = ()
    functional = ()
    adme = ()
    physicochemical = ()

    @property
    def character(self) -> str:
        return {
            AssayType.binding: "B",
            AssayType.functional: "F",
            AssayType.adme: "A",
            AssayType.physicochemical: "P",
        }[self]


__all__ = ["ActivityRelation", "AssayType", "DataValidityComment"]
