"""
Command-line interface for mandos.
"""

from __future__ import annotations

from typing import Type

import typer
from typer.models import CommandInfo

from mandos import MandosLogging, logger
from mandos.commands import MiscCommands
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
        info = CommandInfo(entry.cmd(), callback=entry.run)
        cli.registered_commands.append(info)
        # print(f"Registered {entry.cmd()} to {entry}")
        setattr(SearchCommands, entry.cmd(), entry.run)

    cli.registered_commands.extend(
        [
            CommandInfo(":search", callback=MiscCommands.search),
            CommandInfo(":export:tax-tree", callback=MiscCommands.build_taxonomy),
            CommandInfo(":tax:dl", callback=MiscCommands.dl_tax, hidden=True),
            CommandInfo(":cache", callback=MiscCommands.find),
            CommandInfo(":concat", callback=MiscCommands.concat),
            CommandInfo(":filter", callback=MiscCommands.filter),
            CommandInfo(":filter:taxa", callback=MiscCommands.filter_taxa),
            CommandInfo(":export:copy", callback=MiscCommands.copy),
            CommandInfo(":export:state", callback=MiscCommands.state),
            CommandInfo(":export:reify", callback=MiscCommands.reify),
            CommandInfo(":export:db", callback=MiscCommands.deposit),
            CommandInfo(":serve", callback=MiscCommands.serve),
            CommandInfo(":calc:scores", callback=MiscCommands.score),
            CommandInfo(":calc:matrix", callback=MiscCommands.matrix),
            CommandInfo(":calc:matrix-concordance", callback=MiscCommands.concordance),
        ]
    )


_init_commands()


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
