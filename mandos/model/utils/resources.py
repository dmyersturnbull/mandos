import typing
from pathlib import Path
from typing import Union, Optional

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.hashers import Hasher
from pocketutils.tools.common_tools import CommonTools

from mandos.model.utils.misc_utils import MiscUtils


class MandosResources:

    start_time = MiscUtils.utc()
    start_time_local = start_time.astimezone()
    start_timestamp = start_time.isoformat(timespec="milliseconds")
    start_timestamp_filesys = start_time_local.strftime("%Y-%m-%d_%H-%M-%S")
    hasher: Hasher = Hasher("sha256", buffer_size=16 * 1024)

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

    strings = {k.partition(":")[0]: v for k, v in json("strings.json").items()}


__all__ = ["MandosResources"]
