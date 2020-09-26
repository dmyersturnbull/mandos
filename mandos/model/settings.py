from __future__ import annotations

from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict

instance = ChemblSettings.Instance()


class Settings:
    """"""

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        return Settings(
            data.get_as("mandos.taxon", int, 7742),
            data.get_as("mandos.min_pchembl", float, 7.0),
            data.get_as("mandos.min_confidence_score", int, 4),
            data.get_as("mandos.min_phase", int, 3),
            data.get_as("chembl.cache_path", Path, Path.home() / ".mandos" / "chembl"),
            data.get_as("chembl.n_retries", int, 1),
            data.get_as("chembl.fast_save", bool, True),
            data.get_as("chembl.timeout_sec", int, 1),
        )

    def __init__(
        self,
        taxon: int,
        min_pchembl: float,
        min_confidence_score: int,
        min_phase: int,
        cache_path: Path,
        n_retries: int,
        fast_save: bool,
        timeout_sec: int,
    ):
        """

        Args:
            taxon:
            min_pchembl:
            min_phase:
            cache_path:
            n_retries:
            fast_save:
            timeout_sec:
        """
        self.taxon = taxon
        self.min_pchembl = min_pchembl
        self.min_confidence_score = min_confidence_score
        self.min_phase = min_phase
        self.cache_path = cache_path
        self.n_retries = n_retries
        self.fast_save = fast_save
        self.timeout_sec = timeout_sec

    def set(self):
        """

        Returns:

        """
        instance.CACHING = True
        instance.CACHE_NAME = str(self.cache_path)
        instance.TOTAL_RETRIES = self.n_retries
        instance.FAST_SAVE = self.fast_save
        instance.TIMEOUT = self.timeout_sec


__all__ = ["Settings"]
