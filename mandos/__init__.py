"""
Metadata for this project.
"""

import enum
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as __load
from pathlib import Path
from typing import Union, Mapping, Any

from pocketutils.core.dot_dict import NestedDotDict

pkg = Path(__file__).absolute().parent.name
logger = logging.getLogger(pkg)
_metadata = None
try:
    _metadata = __load(Path(__file__).absolute().parent.name)
    __status__ = "Development"
    __copyright__ = "Copyright 2016–2021"
    __date__ = "2020-08-14"
    __uri__ = _metadata["home-page"]
    __title__ = _metadata["name"]
    __summary__ = _metadata["summary"]
    __license__ = _metadata["license"]
    __version__ = _metadata["version"]
    __author__ = _metadata["author"]
    __maintainer__ = _metadata["maintainer"]
    __contact__ = _metadata["maintainer"]
except PackageNotFoundError:  # pragma: no cover
    logger.error(f"Could not load package metadata for {pkg}. Is it installed?")


class MandosResources:
    @classmethod
    def metadata(cls) -> Mapping[str, Any]:
        # noinspection PyTypeChecker
        return _metadata

    @classmethod
    def path(cls, *nodes: Union[Path, str]) -> Path:
        """Gets a path of a test resource file under resources/."""
        return Path(Path(__file__).parent, "resources", *nodes)

    @classmethod
    def json(cls, *nodes: Union[Path, str]) -> NestedDotDict:
        return NestedDotDict.read_json(Path(Path(__file__).parent, "resources", *nodes))


class QueryType(enum.Enum):
    """
    X
    """

    inchi = enum.auto()
    inchikey = enum.auto()
    chembl = enum.auto()
    smiles = enum.auto()


class MandosUtils:
    @classmethod
    def stars(cls, pvalue: float) -> str:
        for k, v in {0.001: "*" * 4, 0.005: "*" * 3, 0.01: "*" * 2, 0.05: "*", 0.1: "+"}.items():
            if pvalue < k:
                return v
        return "ns"

    @classmethod
    def get_query_type(cls, inchikey: str) -> QueryType:
        """
        Returns the type of query.

        Args:
            inchikey:

        Returns:

        """
        if inchikey.startswith("InChI="):
            return QueryType.inchi
        elif re.compile(r"[A-Z]{14}-[A-Z]{10}-[A-Z]").fullmatch(inchikey):
            return QueryType.inchikey
        elif re.compile(r"CHEMBL[0-9]+").fullmatch(inchikey):
            return QueryType.chembl
        else:
            return QueryType.smiles


if __name__ == "__main__":  # pragma: no cover
    if _metadata is not None:
        print(f"{pkg} (v{_metadata['version']})")
    else:
        print("Unknown project info")


__all__ = ["MandosResources", "QueryType", "MandosUtils"]
