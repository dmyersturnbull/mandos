from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict

instance = ChemblSettings.Instance()
IN_CLI = "IS_IN_CI" in os.environ


@dataclass(frozen=True, repr=True, unsafe_hash=True)
class Settings:
    """"""

    is_testing: bool
    taxon: int
    min_pchembl: float
    min_confidence_score: int
    min_phase: int
    cache_path: Path
    n_retries: int
    fast_save: bool
    timeout_sec: int

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        if IN_CLI:
            cache_path = (
                Path(__file__).parent.parent.parent / "tests" / "resources" / ".mandos-cache"
            )
        else:
            cache_path = Path.home() / ".mandos" / "chembl"
        return Settings(
            data.get_as("is_testing", bool, False),
            data.get_as("mandos.taxon", int, 7742),
            data.get_as("mandos.min_pchembl", float, 6.0),
            data.get_as("mandos.min_confidence_score", int, 4),
            data.get_as("mandos.min_phase", int, 3),
            data.get_as("chembl.cache_path", Path, cache_path),
            data.get_as("chembl.n_retries", int, 1),
            data.get_as("chembl.fast_save", bool, True),
            data.get_as("chembl.timeout_sec", int, 1),
        )

    def set(self):
        """

        Returns:

        """
        instance.CACHING = True
        if not IN_CLI:  # not sure if this is needed
            instance.CACHE_NAME = str(self.cache_path)
        instance.TOTAL_RETRIES = self.n_retries
        instance.FAST_SAVE = self.fast_save
        instance.TIMEOUT = self.timeout_sec


__all__ = ["Settings"]
