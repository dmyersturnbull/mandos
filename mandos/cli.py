"""
Command-line interface for mandos.
"""

from __future__ import annotations

from typing import Type

import typer
from typer.models import CommandInfo

from mandos.model.utils.setup import MandosLogging, logger

from mandos.entry.calc_commands import CalcCommands

# noinspection PyProtectedMember
from mandos.entry.misc_commands import MiscCommands, _InsertedCommandListSingleton
from mandos.entry.api_singletons import Apis
from mandos.entry.entry_commands import Entries
from mandos.entry.plot_commands import PlotCommands
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
        CommandInfo(":document", callback=MiscCommands.document),
        CommandInfo(":search", callback=MiscCommands.search),
        CommandInfo(":detail-search", callback=MiscCommands.detail_search),
        CommandInfo(":defaults", callback=MiscCommands.list_default_settings, hidden=True),
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
