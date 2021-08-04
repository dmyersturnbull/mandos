from __future__ import annotations

import abc
import enum
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypeVar, Union

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools

from mandos import logger
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.utils import MiscUtils


class Api(metaclass=abc.ABCMeta):
    """ """


class CompoundNotFoundError(LookupError):
    """ """


class MultipleMatchesError(ValueError):
    """ """


T = TypeVar("T", covariant=True)


@dataclass(frozen=True, repr=True, order=True)
class CompoundStruct:
    """
    Uniform data view for ChEMBL, PubChem, etc.
    Contains the source db (e.g. "pubchem"), the ID as a str, the inchi, and the inchikey.
    """

    db: str
    id: str
    inchi: str
    inchikey: str

    @property
    def simple_str(self) -> str:
        db = "" if self.db.lower() == "chembl" else self.db + " "
        return f"[{db}{self.id} : {self.inchikey}]"


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
    def of(cls, s: Union[int, str, __qualname__]) -> __qualname__:
        """
        Turns a string or int into this type.
        Case-insensitive. Replaces `` `` and ``-`` with ``_``.
        """
        if isinstance(s, cls):
            return s
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
            logger.error(f"Value {key} not found. Using TargetType.unknown.")
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
        """Gets a path of a test resource file under ``resources/``."""
        path = Path(Path(__file__).parent.parent, "resources", *nodes)
        return path.with_suffix(path.suffix if suffix is None else suffix)

    @classmethod
    def a_path(cls, *nodes: Union[Path, str], suffixes: Optional[typing.Set[str]] = None) -> Path:
        """Gets a path of a test resource file under ``resources/``, ignoring suffix."""
        path = Path(Path(__file__).parent.parent, "resources", *nodes)
        return CommonTools.only(
            [
                p
                for p in path.parent.glob(path.stem + "*")
                if p.is_file() and (suffixes is None or p.suffix in suffixes)
            ]
        )

    @classmethod
    def json(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> NestedDotDict:
        """Reads a JSON file under ``resources/``."""
        return NestedDotDict.read_json(cls.path(*nodes, suffix=suffix))


START_TIME = MiscUtils.utc()
# START_TIMESTAMP = START_TIME.isoformat(timespec="milliseconds")
START_TIMESTAMP = (
    START_TIME.isoformat(timespec="milliseconds").replace(":", "").replace(".", "").replace("-", "")
)


__all__ = [
    "Api",
    "CompoundStruct",
    "CompoundNotFoundError",
    "MandosResources",
    "CleverEnum",
    "START_TIME",
    "START_TIMESTAMP",
]
