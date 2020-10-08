from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict

instance = ChemblSettings.Instance()
_IS_IN_CI = "IS_IN_CI" in os.environ
if _IS_IN_CI:
    DEFAULT_MANDOS_CACHE = (
        Path(__file__).parent.parent.parent / "tests" / "resources" / ".mandos-cache"
    )
else:
    DEFAULT_MANDOS_CACHE = Path(
        {k.lower(): v for k, v in os.environ}.get("MANDOS_HOME", Path.home() / ".mandos")
    )

DEFAULT_CHEMBL_CACHE = DEFAULT_MANDOS_CACHE / "chembl"
DEFAULT_TAXONOMY_CACHE = DEFAULT_MANDOS_CACHE / "taxonomy"


@dataclass(frozen=True, repr=True, unsafe_hash=True)
class Settings:
    """"""

    is_testing: bool
    traversal_strategy: Optional[str]
    taxon: int
    min_pchembl: float
    min_confidence_score: int
    min_phase: int
    cache_path: Path
    chembl_cache_path: Path
    n_retries: int
    fast_save: bool
    timeout_sec: int

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        mandos_home = data.get_as("mandos.cache_path", Path, DEFAULT_MANDOS_CACHE)
        chembl_cache_path = data.get_as("chembl.cache_path", Path, mandos_home / "chembl")
        return Settings(
            data.get_as("is_testing", bool, False),
            data.get_as("mandos.traversal_strategy", None),
            data.get_as("mandos.taxon", int, 7742),
            data.get_as("mandos.min_pchembl", float, 6.0),
            data.get_as("mandos.min_confidence_score", int, 4),
            data.get_as("mandos.min_phase", int, 3),
            mandos_home,
            chembl_cache_path,
            data.get_as("chembl.n_retries", int, 1),
            data.get_as("chembl.fast_save", bool, True),
            data.get_as("chembl.timeout_sec", int, 1),
        )

    @property
    def taxonomy_cache_path(self) -> Path:
        return self.cache_path / "taxonomy"

    def set(self):
        """

        Returns:

        """
        instance.CACHING = True
        if not _IS_IN_CI:  # not sure if this is needed
            instance.CACHE_NAME = str(self.chembl_cache_path)
        instance.TOTAL_RETRIES = self.n_retries
        instance.FAST_SAVE = self.fast_save
        instance.TIMEOUT = self.timeout_sec


__all__ = ["Settings", "DEFAULT_MANDOS_CACHE", "DEFAULT_CHEMBL_CACHE", "DEFAULT_TAXONOMY_CACHE"]
