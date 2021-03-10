from __future__ import annotations

from pathlib import Path
from typing import Union

from pocketutils.core.dot_dict import NestedDotDict


class CompoundNotFoundError(LookupError):
    """"""


class MandosResources:
    @classmethod
    def path(cls, *nodes: Union[Path, str]) -> Path:
        """Gets a path of a test resource file under resources/."""
        return Path(Path(__file__).parent, "resources", *nodes)

    @classmethod
    def json(cls, *nodes: Union[Path, str]) -> NestedDotDict:
        return NestedDotDict.read_json(Path(Path(__file__).parent, "resources", *nodes))


__all__ = ["CompoundNotFoundError", "MandosResources"]
