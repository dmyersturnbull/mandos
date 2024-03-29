from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Any, Collection, Mapping, Optional, Type, TypeVar, Union

from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.exceptions import ConfigError, DirDoesNotExistError, XValueError
from pocketutils.core.query_utils import QueryExecutor
from pocketutils.tools.common_tools import CommonTools
from pocketutils.tools.sys_tools import SystemTools
from suretime import Suretime
from typeddfs import FileFormat, FrozeDict

from mandos.model.utils.globals import Globals
from mandos.model.utils.setup import LOG_SETUP, MandosResources, logger

defaults: Mapping[str, Any] = FrozeDict(MandosResources.json_dict("default_settings.json"))
max_coeff = 1.1
T = TypeVar("T")


@dataclass(frozen=True, repr=True)
class Settings:
    """ """

    is_testing: bool
    ntp_continent: str
    table_suffix: str
    log_suffix: str
    cache_path: Path
    cache_gzip: bool
    save_every: int
    sanitize_paths: bool
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
    selenium_driver: str
    selenium_driver_path: Optional[Path]
    log_signals: bool
    log_exit: bool

    @property
    def as_dict(self) -> Mapping[str, Any]:
        return dataclasses.asdict(self)

    @property
    def all_cache_paths(self) -> AbstractSet[Path]:
        return {
            self.chembl_cache_path,
            self.pubchem_cache_path,
            self.g2p_cache_path,
            self.hmdb_cache_path,
            self.taxonomy_cache_path,
        }

    @property
    def driver_path(self) -> Path:
        return self.cache_path / "driver"

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

    def __post_init__(self):
        # check these things
        FileFormat.from_suffix(self.table_suffix)
        FileFormat.from_suffix(self.archive_filename_suffix)
        LOG_SETUP.guess_file_sink_info(self.log_suffix)
        for k, v in self.as_dict.items():
            # this happens to work for now -- we have none that can be < 0
            if isinstance(v, (int, float)) and v < 0:
                raise XValueError(f"{k} = {v} < 0")

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        extra_default_keys = dict(defaults)

        def get(s: str, t: Type[T]) -> T:
            if s in extra_default_keys:  # could be accessed more than once
                del extra_default_keys[s]
            try:
                return data.get_as(s, t, defaults[s])
            except TypeError:
                raise ConfigError(f"Key {s}={data.get(s), defaults[s]} is not of type {t}")

        _continent = Suretime.Types.NtpContinents.of
        _selenium_path = get("query.selenium_driver_path", Path)
        if _selenium_path is not None:
            _selenium_path = _selenium_path.expanduser()
        chembl_delay = get("query.chembl.delay_sec", float)
        pubchem_delay = get("query.pubchem.delay_sec", float)
        hmdb_delay = get("query.hmdb.delay_sec", float)
        data = cls(
            is_testing=get("is_testing", bool),
            ntp_continent=get("search.ntp_continent_code", _continent),
            table_suffix=get("search.default_table_suffix", str),
            log_suffix=get("search.default_log_suffix", str),
            save_every=get("search.save_every", int),
            sanitize_paths=get("search.sanitize_paths", bool),
            cache_path=Path(get("cache.path", str)).expanduser(),
            chembl_expire_sec=get("cache.chembl.expire_sec", int),
            pubchem_expire_sec=get("cache.pubchem.expire_sec", int),
            taxon_expire_sec=get("cache.taxa.expire_sec", int),
            cache_gzip=get("cache.gzip", bool),
            archive_filename_suffix=get("cache.archive_filename_suffix", str),
            chembl_n_tries=get("query.chembl.n_tries", int),
            chembl_fast_save=get("query.chembl.fast_save", bool),
            chembl_timeout_sec=get("query.chembl.timeout_sec", int),
            chembl_backoff_factor=get("query.chembl.backoff_factor", float),
            chembl_query_delay_min=chembl_delay,
            chembl_query_delay_max=chembl_delay * max_coeff,
            pubchem_timeout_sec=get("query.pubchem.timeout_sec", int),
            hmdb_expire_sec=get("cache.hmdb.expire_sec", int),
            pubchem_backoff_factor=get("query.pubchem.backoff_factor", float),
            pubchem_query_delay_min=get("query.pubchem.delay_sec", float),
            pubchem_query_delay_max=pubchem_delay * max_coeff,
            pubchem_n_tries=get("query.pubchem.n_tries", int),
            hmdb_timeout_sec=get("query.hmdb.timeout_sec", int),
            hmdb_backoff_factor=get("query.hmdb.backoff_factor", float),
            hmdb_query_delay_min=hmdb_delay,
            hmdb_query_delay_max=hmdb_delay * max_coeff,
            selenium_driver=get("query.selenium_driver", str).title(),
            selenium_driver_path=_selenium_path,
            log_signals=get("cli.log_signals", bool),
            log_exit=get("cli.log_exit", bool),
        )
        # we got all the required fields
        # make sure we don't have extra keys in defaults
        if len(extra_default_keys) > 0:
            raise AssertionError(
                f"There are {len(extra_default_keys)} extra defaults"
                + f"in {defaults}: {extra_default_keys}"
            )
        return data

    @classmethod
    def defaults(cls) -> Mapping[str, Any]:
        return defaults

    def configure(self):
        """ """
        # this is a little hacky, but we want to delay logging till now
        if Globals.settings_path.exists():
            logger.success(f"Read settings at {Globals.settings_path}")
        else:
            logger.success(f"Using defaults (no file at {Globals.settings_path})")
        if self.log_exit:
            SystemTools.trace_exit(CommonTools.make_writer(logger.trace))
        if self.log_signals:
            SystemTools.trace_signals(CommonTools.make_writer(logger.trace))

    def configure_chembl(self):
        from chembl_webresource_client.settings import Settings as ChemblSettings

        if not Globals.disable_chembl:
            instance = ChemblSettings.Instance()
            instance.CACHING = True
            instance.CACHE_NAME = str(self.chembl_cache_path.resolve() / "chembl.sqlite")
            logger.debug(f"ChEMBL cache is at {instance.CACHE_NAME}")
            instance.TOTAL_RETRIES = self.chembl_n_tries
            instance.FAST_SAVE = self.chembl_fast_save
            instance.TIMEOUT = self.chembl_timeout_sec
            instance.BACKOFF_FACTOR = self.chembl_backoff_factor
            instance.CACHE_EXPIRE = self.chembl_expire_sec

    @classmethod
    def set_path_for_selenium(cls) -> None:
        cls.add_to_path([SETTINGS.driver_path, MandosResources.dir(), Globals.install_path])

    @classmethod
    def add_to_path(cls, paths: Collection[Union[None, str, Path]]) -> None:
        paths = {Path(p) for p in paths if p is not None}
        for path in paths:
            if path.exists() and not path.is_dir() and not path.is_mount():
                raise DirDoesNotExistError(f"Path {path} is not a directory or mount")
        paths = os.pathsep.join({str(p) for p in paths})
        if len(paths) > 0:
            os.environ["PATH"] += os.pathsep + paths
        logger.debug(f"Added to PATH: {paths}")


if Globals.settings_path.exists():
    SETTINGS = Settings.from_file(Globals.settings_path)
else:
    SETTINGS = Settings.empty()


class QueryExecutors:
    chembl = QueryExecutor(SETTINGS.chembl_query_delay_min, SETTINGS.chembl_query_delay_max)
    pubchem = QueryExecutor(SETTINGS.pubchem_query_delay_min, SETTINGS.pubchem_query_delay_max)
    hmdb = QueryExecutor(SETTINGS.hmdb_query_delay_min, SETTINGS.hmdb_query_delay_max)


QUERY_EXECUTORS = QueryExecutors


__all__ = ["QUERY_EXECUTORS", "SETTINGS"]
