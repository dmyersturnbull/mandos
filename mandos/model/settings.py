from __future__ import annotations

from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict

instance = ChemblSettings.Instance()


class Settings:
    """"""

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        return Settings(
            data.get_as("mandos.taxon", int, 117571),
            data.get_as("mandos.pchembl", float, 7),
            data.get_as("chembl.cache_path", Path, Path.home() / ".mandos" / "chembl"),
            data.get_as("chembl.n_retries", int, 1),
            data.get_as("chembl.fast_save", bool, True),
            data.get_as("chembl.timeout_sec", str, 1),
        )

    def __init__(self, taxon: int, pchembl: float, cache_path: Path, n_retries: int, fast_save: bool, timeout_sec: int):
        """

        Args:
            taxon:
            pchembl: int
            cache_path:
            n_retries:
            fast_save:
            timeout_sec:
        """
        self.taxon = taxon
        self.pchembl = pchembl
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

    def write(self, path: Path) -> None:
        path.write_text(str(self.__dict__), encoding="utf8")


__all__ = ["Settings"]
