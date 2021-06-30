from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools
from suretime import Suretime

from mandos import logger

ONE_YEAR = 60 * 60 * 24 * 365


class Globals:
    chembl_settings = ChemblSettings.Instance()
    is_in_ci = CommonTools.parse_bool(os.environ.get("IS_IN_CI", "false"))
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
    taxonomy_filename_format: str
    default_table_suffix: str

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
            ntp_continent=data.get_as(
                "mandos.continent_code", Suretime.Types.NtpContinents.of, "north-america"
            ),
            cache_path=data.get_as("mandos.cache.path", Path, Globals.mandos_path).expanduser(),
            cache_gzip=data.get_as("mandos.cache.gzip", bool),
            chembl_expire_sec=data.get_as("mandos.query.chembl.expire_sec", int, ONE_YEAR),
            chembl_n_retries=data.get_as("mandos.query.chembl.n_retries", int, 1),
            chembl_fast_save=data.get_as("mandos.query.chembl.fast_save", bool, True),
            chembl_timeout_sec=data.get_as("mandos.query.chembl.timeout_sec", int, 1),
            chembl_backoff_factor=data.get_as(
                "mandos.query.chembl.pubchem_backoff_factor", float, 2
            ),
            chembl_query_delay_min=data.get_as("mandos.query.chembl.delay_sec", float, 0.25),
            chembl_query_delay_max=data.get_as("mandos.query.chembl.delay_sec", float, 0.25),
            pubchem_expire_sec=data.get_as("mandos.query.pubchem.expire_sec", int, ONE_YEAR),
            pubchem_timeout_sec=data.get_as("mandos.query.pubchem.timeout_sec", int, 1),
            pubchem_backoff_factor=data.get_as(
                "mandos.query.pubchem.pubchem_backoff_factor", float, 2
            ),
            pubchem_query_delay_min=data.get_as("mandos.query.pubchem.delay_sec", float, 0.25),
            pubchem_query_delay_max=data.get_as("mandos.query.pubchem.delay_sec", float, 0.25),
            pubchem_n_retries=data.get_as("mandos.query.pubchem.n_retries", int, 1),
            pubchem_use_parent=data.get_as("mandos.query.pubchem.use_parent", bool, True),
            taxonomy_filename_format=data.get_as(
                "mandos.cache.taxonomy_filename_format", str, "{}.feather"
            ),
            default_table_suffix=data.get_as("mandos.default_table_suffix", str, ".feather"),
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
        self.chembl_cache_path.mkdir(exist_ok=True, parents=True)
        self.pubchem_cache_path.mkdir(exist_ok=True, parents=True)
        self.g2p_cache_path.mkdir(exist_ok=True, parents=True)
        self.hmdb_cache_path.mkdir(exist_ok=True, parents=True)
        self.taxonomy_cache_path.mkdir(exist_ok=True, parents=True)
        self.match_cache_path.mkdir(exist_ok=True, parents=True)


if Globals.settings_path.exists():
    MANDOS_SETTINGS = Settings.from_file(Globals.settings_path)
    logger.info(f"Read settings at {Globals.settings_path}")
else:
    MANDOS_SETTINGS = Settings.empty()
    logger.info(f"Using default settings (no file at {Globals.settings_path})")
MANDOS_SETTINGS.configure()
logger.debug(f"Setting ChEMBL cache to {MANDOS_SETTINGS.chembl_cache_path}")


__all__ = ["MANDOS_SETTINGS"]
