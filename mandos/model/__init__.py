from __future__ import annotations

import abc
import logging
import enum
from pathlib import Path
from typing import Optional, Union

from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger("logger")


class CompoundNotFoundError(LookupError):
    """"""


@enum.unique
class CleverEnum(enum.Enum, metaclass=abc.ABCMeta):
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
    def of(cls, s: Union[int, str]) -> __qualname__:
        key = s.replace(" ", "_").replace("-", "_").lower()
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
            logger.error(f"Target type {key} not found. Using TargetType.unknown.")
            if not isinstance(unk, cls):
                raise AssertionError(f"Wrong type {type(unk)} (lookup: {s})")
            return unk


class MandosResources:
    @classmethod
    def contains(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> bool:
        """Returns whether a resource file (or dir) exists."""
        return cls.path(*nodes, suffix=suffix).exists()

    @classmethod
    def path(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> Path:
        """Gets a path of a test resource file under resources/."""
        path = Path(Path(__file__).parent.parent, "resources", *nodes)
        return path.with_suffix(path.suffix if suffix is None else suffix)

    @classmethod
    def json(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> NestedDotDict:
        return NestedDotDict.read_json(cls.path(*nodes, suffix=suffix))


__all__ = ["CompoundNotFoundError", "MandosResources", "CleverEnum"]
