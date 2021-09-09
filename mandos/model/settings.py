from __future__ import annotations

import os
from collections import Set
from dataclasses import dataclass
from pathlib import Path
from typing import Type, TypeVar, Any, Mapping

import orjson
from chembl_webresource_client.settings import Settings as ChemblSettings
from mandos.model.utils.resources import MandosResources
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor
from pocketutils.tools.common_tools import CommonTools
from suretime import Suretime

from mandos.model.utils.setup import logger

defaults = MandosResources.path("default_settings.json").read_text(encoding="utf8")
defaults = orjson.loads(defaults)
T = TypeVar("T")


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
    chembl_n_tries: int
    chembl_timeout_sec: int
    chembl_backoff_factor: float
    chembl_query_delay_min: float
    chembl_query_delay_max: float
    chembl_fast_save: bool
    pubchem_expire_sec: int
    pubchem_n_tries: int
    pubchem_timeout_sec: float
    pubchem_backoff_factor: float
    pubchem_query_delay_min: float
    pubchem_query_delay_max: float
    hmdb_expire_sec: int
    hmdb_timeout_sec: float
    hmdb_backoff_factor: float
    hmdb_query_delay_min: float
    hmdb_query_delay_max: float
    taxon_expire_sec: int
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
    def chembl_scrape_path(self) -> Path:
        return self.chembl_cache_path / "scrape"

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
        def get(s: str, t: Type[T]) -> T:
            return data.get_as(s, t, defaults[s])

        _continent = Suretime.Types.NtpContinents.of
        return cls(
            is_testing=get("is_testing", bool),
            ntp_continent=get("continent_code", _continent),
            cache_path=Path(get("cache.path", str)).expanduser(),
            cache_gzip=get("cache.gzip", bool),
            chembl_expire_sec=get("query.chembl.expire_sec", int),
            chembl_n_tries=get("query.chembl.n_tries", int),
            chembl_fast_save=get("query.chembl.fast_save", bool),
            chembl_timeout_sec=get("query.chembl.timeout_sec", int),
            chembl_backoff_factor=get("query.chembl.backoff_factor", float),
            chembl_query_delay_min=get("query.chembl.delay_sec", float),
            chembl_query_delay_max=get("query.chembl.delay_sec", float),
            pubchem_expire_sec=get("query.pubchem.expire_sec", int),
            pubchem_timeout_sec=get("query.pubchem.timeout_sec", int),
            pubchem_backoff_factor=get("query.pubchem.backoff_factor", float),
            pubchem_query_delay_min=get("query.pubchem.delay_sec", float),
            pubchem_query_delay_max=get("query.pubchem.delay_sec", float),
            pubchem_n_tries=get("query.pubchem.n_tries", int),
            hmdb_expire_sec=get("query.hmdb.expire_sec", int),
            hmdb_timeout_sec=get("query.hmdb.timeout_sec", int),
            hmdb_backoff_factor=get("query.hmdb.backoff_factor", float),
            hmdb_query_delay_min=get("query.hmdb.delay_sec", float),
            hmdb_query_delay_max=get("query.hmdb.delay_sec", float),
            taxon_expire_sec=get("query.taxa.expire_sec", int),
            archive_filename_suffix=get("cache.archive_filename_suffix", str),
            default_table_suffix=get("default_table_suffix", str),
            selenium_driver=get("selenium_driver", str).title(),
        )

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return dict(defaults)

    def configure(self):
        """ """
        if not Globals.disable_chembl:
            instance = Globals.chembl_settings
            instance.CACHING = True
            instance.CACHE_NAME = str(self.chembl_cache_path / "chembl.sqlite")
            instance.TOTAL_RETRIES = self.chembl_n_tries
            instance.FAST_SAVE = self.chembl_fast_save
            instance.TIMEOUT = self.chembl_timeout_sec
            instance.BACKOFF_FACTOR = self.chembl_backoff_factor
            instance.CACHE_EXPIRE = self.chembl_expire_sec


if Globals.settings_path.exists():
    MANDOS_SETTINGS = Settings.from_file(Globals.settings_path)
    logger.info(f"Read settings at {Globals.settings_path}")
else:
    MANDOS_SETTINGS = Settings.empty()
    logger.info(f"Using defaults (no file at {Globals.settings_path})")
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
