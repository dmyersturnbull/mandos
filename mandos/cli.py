"""
Command-line interface for mandos.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, Type

import typer
from loguru import logger
from pocketutils.core import DictNamespace
from pocketutils.misc.loguru_utils import FancyLoguru
from pocketutils.tools.filesys_tools import FilesysTools
from pocketutils.tools.sys_tools import SystemTools
from typer.models import CommandInfo

from mandos.model.utils.globals import Globals

cli = typer.Typer()
# .disable("chembl_webresource_client", "requests_cache", "urllib3", "numba")
_filter = {"": "WARNING", "mandos": "TRACE"}


def _msg(msg: str):
    typer.echo(msg)


def _err(msg: str):
    msg = typer.style(msg, fg=typer.colors.RED)
    typer.echo(msg, err=True)


class CmdNamespace(DictNamespace):
    @classmethod
    def make(cls) -> CmdNamespace:
        from mandos.entry.calc_commands import CalcCommands
        from mandos.entry.entry_commands import Entries
        from mandos.entry.misc_commands import (
            MiscCommands,
            _InsertedCommandListSingleton,
        )
        from mandos.entry.plot_commands import PlotCommands

        cli.registered_commands += [
            CommandInfo(":document", callback=MiscCommands.document),
            CommandInfo(":search", callback=MiscCommands.search),
            CommandInfo(":init", callback=MiscCommands.init, hidden=True),
            CommandInfo(":settings", callback=MiscCommands.list_settings, hidden=True),
            CommandInfo(":fill", callback=MiscCommands.fill),
            CommandInfo(":cache:data", callback=MiscCommands.cache_data),
            CommandInfo(":cache:taxa", callback=MiscCommands.cache_taxa),
            CommandInfo(":cache:g2p", callback=MiscCommands.cache_g2p),
            CommandInfo(":cache:clear", callback=MiscCommands.cache_clear),
            CommandInfo(":export:taxa", callback=MiscCommands.export_taxa),
            CommandInfo(":concat", callback=MiscCommands.concat),
            CommandInfo(":filter", callback=MiscCommands.filter),
            CommandInfo(":export:copy", callback=MiscCommands.export_copy),
            CommandInfo(":export:state", callback=MiscCommands.export_state),
            CommandInfo(":export:reify", callback=MiscCommands.export_reify),
            CommandInfo(":export:db", callback=MiscCommands.export_db, hidden=True),
            CommandInfo(":init-db", callback=MiscCommands.init_db, hidden=True),
            CommandInfo(":serve", callback=MiscCommands.serve, hidden=True),
            CommandInfo(":calc:enrichment", callback=CalcCommands.calc_enrichment),
            CommandInfo(":calc:phi", callback=CalcCommands.calc_phi),
            CommandInfo(":calc:psi", callback=CalcCommands.calc_psi),
            CommandInfo(":calc:ecfp", callback=CalcCommands.calc_ecfp, hidden=True),
            CommandInfo(":calc:psi-projection", callback=CalcCommands.calc_projection),
            CommandInfo(":calc:tau", callback=CalcCommands.calc_tau),
            CommandInfo(":plot:enrichment", callback=PlotCommands.plot_enrichment),
            CommandInfo(":plot:psi-projection", callback=PlotCommands.plot_projection),
            CommandInfo(":plot:psi-heatmap", callback=PlotCommands.plot_heatmap),
            CommandInfo(":plot:phi-vs-psi", callback=PlotCommands.plot_phi_psi),
            CommandInfo(":plot:tau", callback=PlotCommands.plot_tau),
        ]
        commands = {c.name: c for c in cli.registered_commands}
        # Oh dear this is a nightmare
        # it's really hard to create typer commands with dynamically configured params --
        # we really need to rely on its inferring of params
        # that makes this really hard to do well
        for entry in Entries:
            cmd = entry.cmd()
            info = CommandInfo(cmd, callback=entry.run)
            cli.registered_commands.append(info)
            # print(f"Registered {entry.cmd()} to {entry}")
            commands[cmd] = entry.run
        _InsertedCommandListSingleton.commands = cli.registered_commands
        return cls(**commands)


class MandosCli:
    """
    Global entry point for various stuff.
    """

    cli = cli
    commands = None
    log_setup: FancyLoguru = None

    @classmethod
    def as_library(cls) -> Type[MandosCli]:
        from mandos.model.utils.setup import LOG_SETUP

        Globals.is_cli = False
        cls.log_setup = (
            LOG_SETUP.set_control(False)
            .config_levels(
                levels=LOG_SETUP.defaults.levels_extended,
                icons=LOG_SETUP.defaults.icons_extended,
                colors=LOG_SETUP.defaults.colors_extended,
            )
            .add_log_methods()
        )
        cls.start()
        cls.commands = CmdNamespace.make()
        return cls

    @classmethod
    def as_cli(cls) -> Type[MandosCli]:
        from mandos.model.utils.setup import LOG_SETUP

        Globals.is_cli = True
        cls.log_setup = LOG_SETUP.logger.remove(None)
        cls.log_setup = (
            LOG_SETUP.set_control(True)
            .config_levels(
                levels=LOG_SETUP.defaults.levels_extended,
                icons=LOG_SETUP.defaults.icons_extended,
                colors=LOG_SETUP.defaults.colors_red_green_safe,
            )
            .add_log_methods()
            .config_main(fmt=LOG_SETUP.defaults.fmt_simplified, filter=_filter)
            .intercept_std()
        )
        cls.start()
        cls.commands = CmdNamespace.make()
        cls.init_apis()
        return cls

    @classmethod
    def init_apis(cls):
        from mandos.entry.api_singletons import Apis

        Apis.set_default()

    @classmethod
    def start(cls):
        from mandos import MandosMetadata
        from mandos.model.utils.setup import logger

        if MandosMetadata.version is None:
            logger.error("Could not load package metadata for mandos. Is it installed?")
        else:
            logger.info(f"Mandos v{MandosMetadata.version}")


class MandosTyperCli:
    def __init__(self):
        self._mandos = None

    def main(self) -> None:
        try:
            self._mandos = MandosCli.as_cli()
            self._mandos.cli()
            _err("Done! Exited successfully.")
            if self.log_path:
                _err(f"See the log file: {self.log_path.resolve()}")
            quit(0)
        except (KeyboardInterrupt, typer.Abort) as e:
            self._fail(e, "aborted", abort=True)
            quit(130)
        except SystemExit as e:
            if str(e) == "0":
                _err("Done! Exited successfully.")
                if self.log_path:
                    _err(f"See the log file: {self.log_path.resolve()}")
                quit(0)
            self._fail(e, "unexpected exit", abort=False)
            quit(64)
        except Exception as e:
            self._fail(e, "error", abort=False)
            quit(70)
        except BaseException as e:
            self._fail(e, "system error", abort=False)
            quit(71)

    @property
    def log_setup(self) -> Optional[FancyLoguru]:
        if self._mandos and self._mandos.log_setup:
            return self._mandos.log_setup

    @property
    def log_path(self) -> Optional[Path]:
        if self._mandos and self._mandos.log_setup:
            return self._mandos.log_setup.only_path

    def _fail(self, e: BaseException, what: str, *, abort: bool) -> None:
        _err("")
        _err(f"--- {what} ---".upper())
        dump_path = None
        if not abort:
            msg = "\n".join(SystemTools.serialize_exception_msg(e)).strip()
            if len(msg) > 0:
                _err("")
                _err(f"-- Command failed: {msg} --")
            logger.opt(exception=True).critical(f"Command failed: {msg}")
            dump_path = self._dump_error(e)
        if self.log_path:
            _err(f"See the log file: {self.log_path.resolve()}")
        if not abort:
            if dump_path:
                _err(f"Wrote error and system info to: {dump_path}")
            else:
                _err("Note: Failed to write an error dump")
        time.sleep(0.05)  # flush, etc.
        _err("")

    def _dump_error(self, e: BaseException) -> Optional[Path]:
        try:
            return FilesysTools.dump_error(e)
        except BaseException:
            return None


if __name__ == "__main__":
    MandosTyperCli().main()


__all__ = ["CmdNamespace", "MandosCli"]
