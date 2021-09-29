import os
import typing
from datetime import datetime, timedelta
from pathlib import Path
from typing import MutableMapping, Optional, TypeVar, Union

import orjson
import pint
from pint import Quantity
from pint.errors import PintTypeError
from pocketutils.core.chars import Chars
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import FileDoesNotExistError, MissingResourceError, PathExistsError
from pocketutils.core.hashers import Hasher
from pocketutils.tools.common_tools import CommonTools
from pocketutils.tools.unit_tools import UnitTools

from mandos import logger

_UNIT_REG = pint.UnitRegistry()
T = TypeVar("T", covariant=True)


class MandosResources:

    hasher: Hasher = Hasher("sha256", buffer_size=16 * 1024)
    resource_dir = Path(__file__).parent.parent.parent

    @classmethod
    def contains(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> bool:
        """Returns whether a resource file (or dir) exists."""
        return cls.path(*nodes, suffix=suffix).exists()

    @classmethod
    def path(
        cls, *nodes: Union[Path, str], suffix: Optional[str] = None, exists: bool = False
    ) -> Path:
        """Gets a path of a test resource file under ``resources/``."""
        path = Path(cls.resource_dir, "resources", *nodes)
        path = path.with_suffix(path.suffix if suffix is None else suffix)
        if exists and not path.exists():
            raise MissingResourceError(f"Resource {path} missing")
        return path

    @classmethod
    def file(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> Path:
        """Gets a path of a test resource file under ``resources/``."""
        path = cls.path(*nodes, suffix=suffix)
        if not path.is_file():
            raise PathExistsError(f"Resource {path} is not a file!")
        if not os.access(path, os.R_OK):
            raise FileDoesNotExistError(f"Resource {path} is not readable")
        return path

    @classmethod
    def dir(cls, *nodes: Union[Path, str]) -> Path:
        """Gets a path of a test resource file under ``resources/``."""
        path = cls.path(*nodes)
        if not path.is_dir() and not path.is_mount():
            raise PathExistsError(f"Resource {path} is not a directory!")
        return path

    @classmethod
    def a_file(cls, *nodes: Union[Path, str], suffixes: Optional[typing.Set[str]] = None) -> Path:
        """Gets a path of a test resource file under ``resources/``, ignoring suffix."""
        path = Path(cls.resource_dir, "resources", *nodes)
        options = [
            p
            for p in path.parent.glob(path.stem + "*")
            if p.is_file() and (suffixes is None or p.suffix in suffixes)
        ]
        try:
            return CommonTools.only(options)
        except LookupError:
            raise MissingResourceError(f"Resource {path} missing") from None

    @classmethod
    def json(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> NestedDotDict:
        """Reads a JSON file under ``resources/``."""
        path = cls.path(*nodes, suffix=suffix)
        data = orjson.loads(Path(path).read_text(encoding="utf8"))
        return NestedDotDict(data)

    @classmethod
    def json_dict(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> MutableMapping:
        """Reads a JSON file under ``resources/``."""
        path = cls.path(*nodes, suffix=suffix)
        data = orjson.loads(Path(path).read_text(encoding="utf8"))
        return data

    strings = None

    @classmethod
    def check_expired(cls, path: Path, max_sec: Union[timedelta, int], what: str) -> bool:
        if isinstance(max_sec, timedelta):
            max_sec = max_sec.total_seconds()
        # getting the mod date because creation dates are iffy cross-platform
        # (in fact the Linux kernel doesn't bother to expose them)
        when = datetime.fromtimestamp(path.stat().st_mtime)
        delta_sec = (datetime.now() - when).total_seconds()
        if delta_sec > max_sec:
            delta_str = UnitTools.delta_time_to_str(Chars.narrownbsp)
            if delta_sec > 60 * 60 * 24 * 2:
                logger.warning(
                    f"{what} may be {delta_str} out of date. [downloaded: {when.strftime('%Y-%m-%d')}]"
                )
            else:
                logger.warning(
                    f"{what} may be {delta_str} out of date. [downloaded: {when.strftime('%Y-%m-%d %H:%M:%s')}]"
                )
            return True
        return False

    @classmethod
    def canonicalize_quantity(cls, s: str, dimensionality: str) -> Quantity:
        """
        Returns a quantity in reduced units from a magnitude with units.

        Args:
            s: The string to parse; e.g. ``"1 m/s^2"``.
               Unit names and symbols permitted, and spaces may be omitted.
            dimensionality: The resulting Quantity is check against this;
                            e.g. ``"[length]/[meter]^2"``

        Returns:
            a pint ``Quantity``

        Raise:
            PintTypeError: If the dimensionality is inconsistent
        """
        q = _UNIT_REG.Quantity(s).to_reduced_units()
        if not q.is_compatible_with(dimensionality):
            raise PintTypeError(f"{s} not of dimensionality {dimensionality}")
        return q


MandosResources.strings = {
    k.partition(":")[2]: v for k, v in MandosResources.json("strings.json").items()
}


__all__ = ["MandosResources"]
