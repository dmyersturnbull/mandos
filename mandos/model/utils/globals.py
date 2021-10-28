import os
from pathlib import Path

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.tools.common_tools import CommonTools
from suretime import Suretime


class Globals:
    cellular_taxon = 131567
    viral_taxon = 10239
    vertebrata = 7742
    start_time = Suretime.tagged.now_utc_sys().dt
    start_time_local = start_time.astimezone()
    start_timestamp = start_time.isoformat(timespec="milliseconds")
    start_timestamp_filesys = start_time_local.strftime("%Y-%m-%d_%H-%M-%S")
    chembl_settings = ChemblSettings.Instance()
    cwd = os.getcwd()
    where_am_i_installed = Path(__file__).parent.parent.parent
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
    is_cli: bool = False
