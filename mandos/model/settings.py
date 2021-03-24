from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict


logger = logging.getLogger("mandos")


class Globals:
    chembl_settings = ChemblSettings.Instance()
    is_in_ci = "IS_IN_CI" in os.environ
    if is_in_ci:
        mandos_path = Path(__file__).parent.parent.parent / "tests" / "resources" / ".mandos-cache"
    else:
        mandos_path = Path(
            {k.lower(): v for k, v in os.environ.items()}.get(
                "MANDOS_HOME", Path.home() / ".mandos"
            )
        )
    settings_path = mandos_path / "settings.toml"
    chembl_cache = mandos_path / "chembl"
    taxonomy_cache = mandos_path / "taxonomy"


@dataclass(frozen=True, repr=True)
class Settings:
    """"""

    is_testing: bool
    cache_path: Path
    cache_gzip: bool
    chembl_n_retries: int
    chembl_timeout_sec: int
    chembl_query_delay_min: float
    chembl_query_delay_max: float
    chembl_fast_save: bool
    pubchem_n_retries: int
    pubchem_timeout_sec: float
    pubchem_query_delay_min: float
    pubchem_query_delay_max: float
    pubchem_use_parent: bool

    @property
    def chembl_cache_path(self) -> Path:
        return self.cache_path / "chembl"

    @property
    def pubchem_cache_path(self) -> Path:
        return self.cache_path / "pubchem"

    @property
    def hmdb_cache_path(self) -> Path:
        return self.cache_path / "hmdb"

    @property
    def taxonomy_cache_path(self) -> Path:
        return self.cache_path / "taxonomy"

    @property
    def match_cache_path(self) -> Path:
        return self.cache_path / "match"

    @classmethod
    def from_file(cls, path: Path) -> Settings:
        return cls.load(NestedDotDict.read_toml(path))

    @classmethod
    def empty(cls) -> Settings:
        return cls.load(NestedDotDict({}))

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        return cls(
            is_testing=data.get_as("mandos.is_testing", bool, False),
            cache_path=data.get_as("mandos.cache.path", Path, Globals.mandos_path).expanduser(),
            cache_gzip=data.get_as("mandos.cache.gzip", bool),
            chembl_n_retries=data.get_as("mandos.query.chembl.n_retries", int, 1),
            chembl_fast_save=data.get_as("mandos.query.chembl.fast_save", bool, True),
            chembl_timeout_sec=data.get_as("mandos.query.chembl.timeout_sec", int, 1),
            chembl_query_delay_min=data.get_as("mandos.query.chembl.delay_sec", float, 0.25),
            chembl_query_delay_max=data.get_as("mandos.query.chembl.delay_sec", float, 0.25),
            pubchem_timeout_sec=data.get_as("mandos.query.pubchem.timeout_sec", int, 1),
            pubchem_query_delay_min=data.get_as("mandos.query.pubchem.delay_sec", float, 0.25),
            pubchem_query_delay_max=data.get_as("mandos.query.pubchem.delay_sec", float, 0.25),
            pubchem_n_retries=data.get_as("mandos.query.pubchem.n_retries", int, 1),
            pubchem_use_parent=data.get_as("mandos.query.pubchem.use_parent", bool, True),
        )

    def set(self):
        """

        Returns:

        """
        instance = Globals.chembl_settings
        instance.CACHING = True
        if not Globals.is_in_ci:  # not sure if this is needed
            instance.CACHE_NAME = str(self.chembl_cache_path)
            logger.info(f"Setting ChEMBL cache to {self.chembl_cache_path}")
        instance.TOTAL_RETRIES = self.chembl_n_retries
        instance.FAST_SAVE = self.chembl_fast_save
        instance.TIMEOUT = self.chembl_timeout_sec
        self.chembl_cache_path.mkdir(exist_ok=True, parents=True)
        self.pubchem_cache_path.mkdir(exist_ok=True, parents=True)
        self.hmdb_cache_path.mkdir(exist_ok=True, parents=True)
        self.taxonomy_cache_path.mkdir(exist_ok=True, parents=True)
        self.match_cache_path.mkdir(exist_ok=True, parents=True)


if Globals.settings_path.exists():
    MANDOS_SETTINGS = Settings.from_file(Globals.settings_path)
    logger.info(f"Read settings at {Globals.settings_path}")
else:
    MANDOS_SETTINGS = Settings.empty()
    logger.info(f"Using default settings (no file at {Globals.settings_path})")
MANDOS_SETTINGS.set()


__all__ = ["MANDOS_SETTINGS"]
