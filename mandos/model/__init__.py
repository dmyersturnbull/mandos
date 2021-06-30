from __future__ import annotations

import abc
import inspect
import enum
import sys
import typing
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Type, TypeVar, Mapping, Any, Sequence

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools
from suretime import Suretime

from mandos import logger
from mandos.model.settings import MANDOS_SETTINGS


class Api(metaclass=abc.ABCMeta):
    """ """


class CompoundNotFoundError(LookupError):
    """ """


class InjectionError(LookupError):
    """ """


class MultipleMatchesError(ValueError):
    """ """


T = TypeVar("T", covariant=True)


class ReflectionUtils:
    @classmethod
    def get_generic_arg(cls, clazz: Type[T], bound: Optional[Type[T]] = None) -> Type:
        """
        Finds the generic argument (specific TypeVar) of a :py:class:`~typing.Generic` class.
        **Assumes that ``clazz`` only has one type parameter. Always returns the first.**

        Args:
            clazz: The Generic class
            bound: If non-None, requires the returned type to be a subclass of ``bound`` (or equal to it)

        Returns:
            The class

        Raises:
            AssertionError: For most errors
        """
        bases = clazz.__orig_bases__
        try:
            param = typing.get_args(bases[0])[0]
        except KeyError:
            raise AssertionError(f"Failed to get generic type on {cls}")
        if not issubclass(param, bound):
            raise AssertionError(f"{param} is not a {bound}")
        return param

    @classmethod
    def default_arg_values(cls, func) -> Mapping[str, Optional[Any]]:
        return {k: v.default for k, v in cls.optional_args(func).items()}

    @classmethod
    def required_args(cls, func):
        """
        Finds parameters that lack default values.

        Args:
            func: A function or method

        Returns:
            A dict mapping parameter names to instances of ``MappingProxyType``,
            just as ``inspect.signature(func).parameters`` does.
        """
        return cls._args(func, True)

    @classmethod
    def optional_args(cls, func):
        """
        Finds parameters that have default values.

        Args:
            func: A function or method

        Returns:
            A dict mapping parameter names to instances of ``MappingProxyType``,
            just as ``inspect.signature(func).parameters`` does.
        """
        return cls._args(func, False)

    @classmethod
    def _args(cls, func, req):
        signature = inspect.signature(func)
        return {
            k: v
            for k, v in signature.parameters.items()
            if req
            and v.default is inspect.Parameter.empty
            or not req
            and v.default is not inspect.Parameter.empty
        }

    @classmethod
    def injection(cls, fully_qualified: str, clazz: Type[T]) -> Type[T]:
        """
        Gets a **class** by its fully-resolved class name.

        Args:
            fully_qualified:
            clazz:

        Returns:
            The Type

        Raises:
            InjectionError: If the class was not found
        """
        s = fully_qualified
        mod = s[: s.rfind(".")]
        clz = s[s.rfind(".") :]
        try:
            return getattr(sys.modules[mod], clz)
        except AttributeError:
            raise InjectionError(
                f"Did not find {clazz} by fully-qualified class name {fully_qualified}"
            )


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
    def of(cls, s: Union[int, str]) -> __qualname__:
        """
        Turns a string or int into this type.
        Case-insensitive. Replaces `` `` and ``-`` with ``_``.
        """
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

    VERTEBRATA_PATH = None

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


class MiscUtils:
    """
    These are here to make sure I always use the same NTP server, etc.
    """

    @classmethod
    def adjust_filename(cls, to: Optional[Path], default: str, replace: bool) -> Path:
        if to is None:
            return Path(default)
        elif str(to).startswith("."):
            return Path(default).with_suffix(str(to))
        elif to.is_dir() or to.suffix == "":
            return to / default
        if replace or not to.exists():
            return to
        raise FileExistsError(f"File {to} already exists")

    @classmethod
    def ntp_utc(cls) -> datetime:
        ntp = Suretime.tagged.now_utc_ntp(
            ntp_server=MANDOS_SETTINGS.ntp_continent, ntp_clock="client-sent"
        )
        return ntp.use_clock_as_dt.dt

    @classmethod
    def utc(cls) -> datetime:
        return Suretime.tagged.now_utc_sys().dt

    @classmethod
    def serialize_list(cls, lst: Sequence[str]) -> str:
        return " || ".join([str(x) for x in lst])

    @classmethod
    def deserialize_list(cls, s: str) -> Sequence[str]:
        return s.split(" || ")


START_NTP_TIME = MiscUtils.ntp_utc()
START_NTP_TIMESTAMP = START_NTP_TIME.isoformat(timespec="milliseconds")


MandosResources.VERTEBRATA_PATH = MandosResources.a_path("7742")


__all__ = [
    "Api",
    "CompoundNotFoundError",
    "MandosResources",
    "CleverEnum",
    "ReflectionUtils",
    "InjectionError",
    "MiscUtils",
    "START_NTP_TIME",
    "START_NTP_TIMESTAMP",
]
