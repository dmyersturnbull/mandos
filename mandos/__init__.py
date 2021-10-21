"""
Metadata for this project.
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import metadata as __load
from pathlib import Path
from typing import Optional

from mandos.model.utils import logger

_metadata = None
__version__ = None
try:
    _metadata = __load(Path(__file__).absolute().parent.name)
    __status__ = "Development"
    __copyright__ = "Copyright 2020–2021"
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
    logger.error("Could not load package metadata for mandos. Is it installed?")


class MandosMetadata:
    version: Optional[str] = __version__


# weird as hell, but it works
# noinspection PyTypeChecker


if __name__ == "__main__":  # pragma: no cover
    if _metadata is not None:
        print(f"mandos v{__version__}")
    else:
        print("Unknown project info")


__all__ = ["MandosMetadata"]
