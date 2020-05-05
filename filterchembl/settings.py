from __future__ import annotations
from typing import Set
from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings

from filterchembl.utils import Toml

instance = ChemblSettings.Instance()


class Settings:

    @classmethod
    def load(cls, path: Path):
        data = Toml.read(path)
        return Settings(
            set(data.str_list('filters.organisms')),
            data.path('chembl.cache_path', Path.home()/'.chembl-cache'),
            data.int('chembl.n_retries', 1),
            data.get('chembl.fast_save', 1),
            data.get('chembl.timeout_sec', 1)
        )

    def __init__(
        self,
        organisms: Set[str],
        cache_path: Path,
        n_retries: int,
        fast_save: bool,
        timeout_sec: int
    ):
        self.organisms = organisms
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


__all__ = ['Settings']
