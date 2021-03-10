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
    config_path = mandos_path / "settings.toml"
    chembl_cache = mandos_path / "chembl"
    taxonomy_cache = mandos_path / "taxonomy"


@dataclass(frozen=True, repr=True)
class Settings:
    """"""

    is_testing: bool
    cache_path: Path
    cache_gzip: bool
    chembl_n_retries: int
    chembl_fast_save: bool
    chembl_timeout_sec: int
    chembl_min_query_delay: float
    chembl_max_query_delay: float
    pubchem_use_parent_molecule: bool
    pubchem_min_query_delay: float
    pubchem_max_query_delay: float

    @property
    def chembl_cache_path(self) -> Path:
        return self.cache_path / "chembl"

    @property
    def pubchem_cache_path(self) -> Path:
        return self.cache_path

    @classmethod
    def from_file(cls, path: Path) -> Settings:
        return cls.load(NestedDotDict.read_toml(path))

    @classmethod
    def empty(cls) -> Settings:
        return cls.load(NestedDotDict({}))

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        cache_path = data.get_as("mandos.cache_path", Path, Globals.mandos_path)
        return cls(
            is_testing=data.get_as("is_testing", bool, False),
            cache_path=cache_path,
            cache_gzip=data.get_as("mandos.cache.gzip", bool),
            chembl_n_retries=data.get_as("mandos.chembl.n_retries", int, 1),
            chembl_fast_save=data.get_as("mandos.chembl.fast_save", bool, True),
            chembl_timeout_sec=data.get_as("chembl.timeout_sec", int, 1),
            chembl_min_query_delay=data.get_as("mandos.pubchem.query_delay_sec_min", float, 0.25),
            chembl_max_query_delay=data.get_as("mandos.pubchem.query_delay_sec_min", float, 0.25),
            pubchem_min_query_delay=data.get_as("mandos.pubchem.query_delay_sec_min", float, 0.25),
            pubchem_max_query_delay=data.get_as("mandos.pubchem.query_delay_sec_min", float, 0.25),
            pubchem_use_parent_molecule=data.get_as(
                "mandos.pubchem.use_parent_molecule", bool, True
            ),
        )

    @property
    def taxonomy_cache_path(self) -> Path:
        return self.cache_path / "taxonomy"

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


if Globals.mandos_path.exists():
    MANDOS_SETTINGS = Settings.from_file(Globals.mandos_path)
    logger.info(f"Read settings at {Globals.mandos_path}")
else:
    MANDOS_SETTINGS = Settings.empty()
    logger.info(f"Using default settings (no file at {Globals.mandos_path})")
MANDOS_SETTINGS.set()


__all__ = ["MANDOS_SETTINGS"]
