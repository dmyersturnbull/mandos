from pathlib import Path
from typing import TypeVar

from pocketutils.core.exceptions import DbLookupError
from pocketutils.misc.fancy_loguru import FancyLoguruExtras
from pocketutils.misc.resources import Resources

T = TypeVar("T", covariant=True)

MANDOS_SETUP = FancyLoguruExtras.extended()
logger = MANDOS_SETUP.logger


class _MandosResources(Resources):
    def __init__(self, path: Path, ell=logger):
        super().__init__(path, logger=ell)
        self.strings = None


MandosResources = _MandosResources(Path(__file__).parent.parent.parent)
MandosResources.strings = {
    k.partition(":")[2]: v for k, v in MandosResources.json("strings.json").items()
}


class CompoundNotFoundError(DbLookupError):
    """ """


__all__ = ["MandosResources", "MANDOS_SETUP", "logger", "CompoundNotFoundError"]
