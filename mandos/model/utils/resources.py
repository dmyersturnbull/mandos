import os
import typing
from pathlib import Path
from typing import Union, Optional, MutableMapping

import orjson
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import (
    FileDoesNotExistError,
    DirDoesNotExistError,
    MissingResourceError,
    PathExistsError,
)
from pocketutils.core.hashers import Hasher
from pocketutils.tools.common_tools import CommonTools

from mandos.model.utils.misc_utils import MiscUtils


class MandosResources:

    start_time = MiscUtils.utc()
    start_time_local = start_time.astimezone()
    start_timestamp = start_time.isoformat(timespec="milliseconds")
    start_timestamp_filesys = start_time_local.strftime("%Y-%m-%d_%H-%M-%S")
    hasher: Hasher = Hasher("sha256", buffer_size=16 * 1024)
    resource_dir = Path(__file__).parent.parent.parent

    @classmethod
    def contains(cls, *nodes: Union[Path, str], suffix: Optional[str] = None) -> bool:
        """Returns whether a resource file (or dir) exists."""
        return cls.path(*nodes, suffix=suffix).exists()

    @classmethod
    def path(
        cls, *nodes: Union[Path, str], suffix: Optional[str] = None, exists: bool = True
    ) -> Path:
        """Gets a path of a test resource file under ``resources/``."""
        path = Path(cls.resource_dir, "resources", *nodes)
        path = path.with_suffix(path.suffix if suffix is None else suffix)
        if not path.exists():
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


MandosResources.strings = {
    k.partition(":")[2]: v for k, v in MandosResources.json("strings.json").items()
}


__all__ = ["MandosResources"]
