from __future__ import annotations

from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict

instance = ChemblSettings.Instance()


class Settings:
    @classmethod
    def load(cls, path: Path):
        data = NestedDotDict.read_toml(path)
        return Settings(
            data.get_as("chembl.cache_path", Path, Path.home() / ".mandos"),
            data.get_as("chembl.n_retries", int, 1),
            data.get_as("chembl.fast_save", str, 1),
            data.get_as("chembl.timeout_sec", str, 1),
        )

    def __init__(self, cache_path: Path, n_retries: int, fast_save: bool, timeout_sec: int):
        self.cache_path = cache_path
        self.n_retries = n_retries
        self.fast_save = fast_save
        self.timeout_sec = timeout_sec

    def set(self):
        instance.CACHING = True
        instance.CACHE_NAME = str(self.cache_path)
        instance.TOTAL_RETRIES = self.n_retries
        instance.FAST_SAVE = self.fast_save
        instance.TIMEOUT = self.timeout_sec


__all__ = ["Settings"]
