import os
from pathlib import Path

from pocketutils.tools.common_tools import CommonTools
from suretime import Suretime


class Globals:
    start_time = Suretime.tagged.now_utc_sys().dt
    start_time_local = start_time.astimezone()
    start_timestamp = start_time.isoformat(timespec="milliseconds")
    start_timestamp_filesys = start_time_local.strftime("%Y-%m-%d_%H-%M-%S")
    cwd = os.getcwd()
    install_path = Path(__file__).parent.parent.parent
    is_in_ci = CommonTools.parse_bool_flex(os.environ.get("IS_IN_CI", "false"))
    if is_in_ci:
        mandos_path = Path(__file__).parent.parent.parent / "tests" / "resources" / ".mandos-cache"
    else:
        _default_mandos_home = Path.home() / ".mandos"
        env_vars = {k.lower(): v for k, v in os.environ.items()}
        mandos_path = Path(env_vars.get("MANDOS_HOME", _default_mandos_home))
    settings_path = mandos_path / "settings.toml"
    disable_chembl = CommonTools.parse_bool_flex(os.environ.get("MANDOS_NO_CHEMBL", "false"))
    disable_pubchem = CommonTools.parse_bool_flex(os.environ.get("MANDOS_NO_PUBCHEM", "false"))
    is_cli: bool = False


__all__ = ["Globals"]
