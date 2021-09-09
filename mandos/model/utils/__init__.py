import enum
from typing import Optional, Union

from mandos.model.utils.setup import logger


class TrueFalseUnknown(enum.Enum):
    true = enum.auto()
    false = enum.auto()
    unknown = enum.auto()

    @classmethod
    def parse(cls, s: str):
        tf_map = {
            "t": TrueFalseUnknown.true,
            "f": TrueFalseUnknown.false,
            "true": TrueFalseUnknown.true,
            "false": TrueFalseUnknown.false,
        }
        return tf_map.get(s.lower().strip(), TrueFalseUnknown.unknown)


class CleverEnum(enum.Enum):
    """
    An enum with a ``.of`` method that finds values
    with limited string/value fixing.
    May support an "unmatched" type -- a fallback value when there is no match.
    This is similar to pocketutils' simpler ``SmartEnum``.
    It is mainly useful for enums corresponding to concepts in ChEMBL and PubChem,
    where it's acceptable for the user to input spaces (like the database concepts use)
    rather than the underscores that Python requires.
    """

    @classmethod
    def _unmatched_type(cls) -> Optional[__qualname__]:
        return None

    @classmethod
    def or_none(cls, s: Union[int, str, __qualname__]) -> Optional[__qualname__]:
        try:
            return cls.of(s)
        except KeyError:
            return None

    @classmethod
    def of(cls, s: Union[int, str, __qualname__]) -> __qualname__:
        """
        Turns a string or int into this type.
        Case-insensitive. Replaces `` ``, ``.``, and ``-`` with ``_``.
        """
        if isinstance(s, cls):
            return s
        key = s.strip().replace(" ", "_").replace(".", "_").replace("-", "_").lower()
        try:
            if isinstance(s, str):
                return cls[key]
            elif isinstance(key, int):
                return cls(key)
            else:
                raise TypeError(f"Lookup type {type(s)} for value {s} not a str or int")
        except KeyError:
            unk = cls._unmatched_type()
            if unk is None:
                raise
            logger.error(f"Value {key} not found. Using {unk}")
            if not isinstance(unk, cls):
                raise AssertionError(f"Wrong type {type(unk)} (lookup: {s})")
            return unk


__all__ = ["TrueFalseUnknown", "CleverEnum"]
