"""
Command-line interface for mandos.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Optional, Type

import orjson
import typer
from pocketutils.core import DictNamespace
from pocketutils.misc.loguru_utils import FancyLoguru
from pocketutils.tools.filesys_tools import FilesysTools
from typer.models import CommandInfo

from mandos.model.utils.globals import Globals

cli = typer.Typer()
_my_colors = dict(
    TRACE="<dim>",
    DEBUG="<bold>",
    INFO="<cyan>",
    CAUTION="<yellow>",
    SUCCESS="<blue>",
    WARNING="<bold><yellow>",
    NOTICE="<bold><blue>",
    ERROR="<red>",
    CRITICAL="<bold><red>",
)


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
            .disable("chembl_webresource_client", "requests_cache", "urllib3", "numba")
            .config_levels(
                levels=LOG_SETUP.defaults.levels_extended,
                icons=LOG_SETUP.defaults.icons_extended,
                colors=_my_colors,
            )
            .add_log_methods()
            .config_main(fmt=LOG_SETUP.defaults.fmt_simplified)
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
        self._mandos = MandosCli.as_cli()
        try:
            self._mandos.cli()
        except KeyboardInterrupt:
            raise typer.Abort()
        except BaseException as e:
            typer.echo(f"Command failed: {str(e)}", err=True)
            logger = self._mandos.log_setup.logger
            logger.critical(f"Command failed: {str(e)}", exc_info=True)
            log_path = self._log_path()
            if log_path is not None:
                typer.echo(f"See the log file at {log_path}", err=True)
            dmp_path = Path(f"mandos-err-dump-{Globals.start_timestamp_filesys}.json")
            FilesysTools.dump_error(e, dmp_path)
            typer.echo(f"See {dmp_path.resolve()} for details", err=True)
            raise typer.Exit(code=1)

    def _log_path(self) -> Optional[Path]:
        s_ = self._mandos.log_setup
        try:
            return next(iter(s_.paths)).path.resolve()
        except (StopIteration, AttributeError):
            return None


if __name__ == "__main__":
    MandosTyperCli().main()


__all__ = ["CmdNamespace", "MandosCli"]
