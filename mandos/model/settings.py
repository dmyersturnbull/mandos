from __future__ import annotations

import os
from collections import Set
from dataclasses import dataclass
from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor
from pocketutils.tools.common_tools import CommonTools
from suretime import Suretime

from mandos import logger

ONE_MONTH = int(round(60 * 60 * 24 * 30.437))


class Globals:
    chembl_settings = ChemblSettings.Instance()
    is_in_ci = CommonTools.parse_bool(os.environ.get("IS_IN_CI", "false"))
    if is_in_ci:
        mandos_path = Path(__file__).parent.parent.parent / "tests" / "resources" / ".mandos-cache"
    else:
        _default_mandos_home = Path.home() / ".mandos"
        env_vars = {k.lower(): v for k, v in os.environ.items()}
        mandos_path = Path(env_vars.get("MANDOS_HOME", _default_mandos_home))
    settings_path = mandos_path / "settings.toml"
    chembl_cache = mandos_path / "chembl"
    taxonomy_cache = mandos_path / "taxonomy"
    disable_chembl = CommonTools.parse_bool(os.environ.get("MANDOS_NO_CHEMBL", "false"))
    disable_pubchem = CommonTools.parse_bool(os.environ.get("MANDOS_NO_PUBCHEM", "false"))


@dataclass(frozen=True, repr=True)
class Settings:
    """ """

    is_testing: bool
    ntp_continent: str
    cache_path: Path
    cache_gzip: bool
    chembl_expire_sec: int
    chembl_n_retries: int
    chembl_timeout_sec: int
    chembl_backoff_factor: float
    chembl_query_delay_min: float
    chembl_query_delay_max: float
    chembl_fast_save: bool
    pubchem_expire_sec: int
    pubchem_n_retries: int
    pubchem_timeout_sec: float
    pubchem_backoff_factor: float
    pubchem_query_delay_min: float
    pubchem_query_delay_max: float
    pubchem_use_parent: bool
    hmdb_expire_sec: int
    hmdb_timeout_sec: float
    hmdb_backoff_factor: float
    hmdb_query_delay_min: float
    hmdb_query_delay_max: float
    archive_filename_suffix: str
    default_table_suffix: str
    selenium_driver: str

    def __post_init__(self):
        pass

    @property
    def all_cache_paths(self) -> Set[Path]:
        return {
            self.chembl_cache_path,
            self.pubchem_cache_path,
            self.g2p_cache_path,
            self.hmdb_cache_path,
            self.taxonomy_cache_path,
        }

    @property
    def chembl_cache_path(self) -> Path:
        return self.cache_path / "chembl"

    @property
    def pubchem_cache_path(self) -> Path:
        return self.cache_path / "pubchem"

    @property
    def g2p_cache_path(self) -> Path:
        return self.cache_path / "g2p"

    @property
    def hmdb_cache_path(self) -> Path:
        return self.cache_path / "hmdb"

    @property
    def taxonomy_cache_path(self) -> Path:
        return self.cache_path / "taxonomy"

    @classmethod
    def from_file(cls, path: Path) -> Settings:
        return cls.load(NestedDotDict.read_toml(path))

    @classmethod
    def empty(cls) -> Settings:
        return cls.load(NestedDotDict({}))

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        _continent = Suretime.Types.NtpContinents.of
        return cls(
            is_testing=data.get_as("is_testing", bool, False),
            ntp_continent=data.get_as("continent_code", _continent, "north-america"),
            cache_path=data.get_as("cache.path", Path, Globals.mandos_path).expanduser(),
            cache_gzip=data.get_as("cache.gzip", bool),
            chembl_expire_sec=data.get_as("query.chembl.expire_sec", int, ONE_MONTH),
            chembl_n_retries=data.get_as("query.chembl.n_retries", int, 1),
            chembl_fast_save=data.get_as("query.chembl.fast_save", bool, True),
            chembl_timeout_sec=data.get_as("query.chembl.timeout_sec", int, 1),
            chembl_backoff_factor=data.get_as("query.chembl.pubchem_backoff_factor", float, 2),
            chembl_query_delay_min=data.get_as("query.chembl.delay_sec", float, 0.25),
            chembl_query_delay_max=data.get_as("query.chembl.delay_sec", float, 0.25),
            pubchem_expire_sec=data.get_as("query.pubchem.expire_sec", int, ONE_MONTH),
            pubchem_timeout_sec=data.get_as("query.pubchem.timeout_sec", int, 1),
            pubchem_backoff_factor=data.get_as("query.pubchem.pubchem_backoff_factor", float, 2),
            pubchem_query_delay_min=data.get_as("query.pubchem.delay_sec", float, 0.25),
            pubchem_query_delay_max=data.get_as("query.pubchem.delay_sec", float, 0.25),
            pubchem_n_retries=data.get_as("query.pubchem.n_retries", int, 1),
            pubchem_use_parent=data.get_as("query.pubchem.use_parent", bool, True),
            hmdb_expire_sec=data.get_as("query.pubchem.expire_sec", int, ONE_MONTH),
            hmdb_timeout_sec=data.get_as("query.pubchem.timeout_sec", int, 1),
            hmdb_backoff_factor=data.get_as("query.pubchem.pubchem_backoff_factor", float, 2),
            hmdb_query_delay_min=data.get_as("query.pubchem.delay_sec", float, 0.25),
            hmdb_query_delay_max=data.get_as("query.pubchem.delay_sec", float, 0.25),
            archive_filename_suffix=data.get_as("cache.archive_filename_suffix", str, ".snappy"),
            default_table_suffix=data.get_as("default_table_suffix", str, ".feather"),
            selenium_driver=data.get_as("selenium_driver", str, "Chrome").title(),
        )

    def configure(self):
        """ """
        if not Globals.disable_chembl:
            instance = Globals.chembl_settings
            instance.CACHING = True
            if not Globals.is_in_ci:  # not sure if this is needed
                instance.CACHE_NAME = str(self.chembl_cache_path / "chembl.sqlite")
            instance.TOTAL_RETRIES = self.chembl_n_retries
            instance.FAST_SAVE = self.chembl_fast_save
            instance.TIMEOUT = self.chembl_timeout_sec
            instance.BACKOFF_FACTOR = self.chembl_backoff_factor
            instance.CACHE_EXPIRE = self.chembl_expire_sec
        for p in self.all_cache_paths:
            p.mkdir(exist_ok=True, parents=True)


if Globals.settings_path.exists():
    MANDOS_SETTINGS = Settings.from_file(Globals.settings_path)
    logger.info(f"Read settings at {Globals.settings_path}")
else:
    MANDOS_SETTINGS = Settings.empty()
    logger.info(f"Using default settings (no file at {Globals.settings_path})")
MANDOS_SETTINGS.configure()
logger.debug(f"Setting ChEMBL cache to {MANDOS_SETTINGS.chembl_cache_path}")


class QueryExecutors:
    chembl = QueryExecutor(
        MANDOS_SETTINGS.chembl_query_delay_min, MANDOS_SETTINGS.chembl_query_delay_max
    )
    pubchem = QueryExecutor(
        MANDOS_SETTINGS.pubchem_query_delay_min, MANDOS_SETTINGS.pubchem_query_delay_max
    )
    hmdb = QueryExecutor(
        MANDOS_SETTINGS.pubchem_query_delay_min, MANDOS_SETTINGS.pubchem_query_delay_max
    )


QUERY_EXECUTORS = QueryExecutors


__all__ = ["MANDOS_SETTINGS", "QUERY_EXECUTORS"]
