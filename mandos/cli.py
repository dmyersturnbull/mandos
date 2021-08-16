"""
Command-line interface for mandos.
"""

from __future__ import annotations

from typing import Type

import typer
from typer.models import CommandInfo

from mandos import MandosLogging, logger

# noinspection PyUnresolvedReferences
from mandos.commands import MiscCommands, _InsertedCommandListSingleton
from mandos.entries.api_singletons import Apis
from mandos.entries.entries import Entries
from mandos.model.settings import MANDOS_SETTINGS

cli = typer.Typer()


class SearchCommands:
    """
    Entry points for mandos.
    """


def _init_commands():
    # Oh dear this is a nightmare
    # it's really hard to create typer commands with dynamically configured params --
    # we really need to rely on its inferring of params
    # that makes this really hard to do well
    for entry in Entries:
        cmd = entry.cmd()
        info = CommandInfo(cmd, callback=entry.run)
        cli.registered_commands.append(info)
        # print(f"Registered {entry.cmd()} to {entry}")
        setattr(SearchCommands, cmd, entry.run)

    cli.registered_commands += [
        CommandInfo(":search", callback=MiscCommands.search),
        CommandInfo(":describe", callback=MiscCommands.describe),
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
        CommandInfo(":serve", callback=MiscCommands.serve, hidden=True),
        CommandInfo(":calc:analysis", callback=MiscCommands.calc_analysis),
        CommandInfo(":calc:score", callback=MiscCommands.calc_score),
        CommandInfo(":format:phi", callback=MiscCommands.format_phi),
        CommandInfo(":calc:ecfp", callback=MiscCommands.calc_ecfp),
        CommandInfo(":calc:psi", callback=MiscCommands.calc_psi),
        CommandInfo(":calc:project", callback=MiscCommands.calc_project),
        CommandInfo(":calc:tau", callback=MiscCommands.calc_tau),
        CommandInfo(":plot:score", callback=MiscCommands.plot_score),
        CommandInfo(":plot:phi-psi", callback=MiscCommands.plot_phi_psi),
        CommandInfo(":plot:project", callback=MiscCommands.plot_project),
        CommandInfo(":plot:tau", callback=MiscCommands.plot_tau),
    ]


_init_commands()
_InsertedCommandListSingleton.commands = cli.registered_commands


class MandosCli:
    """
    Global entry point for various stuff. For import by consumers.
    """

    settings = MANDOS_SETTINGS
    logger = logger
    logging = MandosLogging
    main = cli
    search_cmds = SearchCommands
    misc_cmds = MiscCommands

    @classmethod
    def init(cls) -> Type[MandosCli]:
        MandosLogging.init()
        Apis.set_default()
        return cls


if __name__ == "__main__":
    MandosCli.init().main()


__all__ = ["MandosCli"]
