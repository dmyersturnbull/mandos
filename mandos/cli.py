"""
Command-line interface for mandos.
"""

from __future__ import annotations

import typing
from pathlib import Path
from typing import Type

import typer
from typer.models import CommandInfo

from mandos import MandosLogging, logger, MANDOS_SETUP
from mandos.commands import MiscCommands
from mandos.docs import Documenter
from mandos.entries.api_singletons import Apis
from mandos.entries.common_args import CommonArgs, Opt, fail
from mandos.entries.entries import Entries
from mandos.model import MiscUtils
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
        CommandInfo(":export:taxa", callback=MiscCommands.build_taxonomy),
        CommandInfo(":cache", callback=MiscCommands.find),
        CommandInfo(":cache:taxa", callback=MiscCommands.dl_tax),
        CommandInfo(":concat", callback=MiscCommands.concat),
        CommandInfo(":filter", callback=MiscCommands.filter),
        CommandInfo(":filter:taxa", callback=MiscCommands.filter_taxa),
        CommandInfo(":export:copy", callback=MiscCommands.copy),
        CommandInfo(":export:state", callback=MiscCommands.state),
        CommandInfo(":export:reify", callback=MiscCommands.reify),
        CommandInfo(":export:db", callback=MiscCommands.deposit, hidden=True),
        CommandInfo(":serve", callback=MiscCommands.serve, hidden=True),
        CommandInfo(":analyze", callback=MiscCommands.analyze),
        CommandInfo(":calc:score", callback=MiscCommands.alpha),
        CommandInfo(":format:phi", callback=MiscCommands.prep_phi),
        CommandInfo(":format:input", callback=MiscCommands.prep_phi),
        CommandInfo(":calc:ecfp", callback=MiscCommands.calc_ecfp_psi),
        CommandInfo(":calc:psi", callback=MiscCommands.psi),
        CommandInfo(":calc:project", callback=MiscCommands.calc_umap),
        CommandInfo(":calc:tau", callback=MiscCommands.tau),
        CommandInfo(":plot:score", callback=MiscCommands.plot_score),
        CommandInfo(":plot:phi-psi", callback=MiscCommands.plot_pairing),
        CommandInfo(":plot:project", callback=MiscCommands.plot_umap),
        CommandInfo(":plot:tau", callback=MiscCommands.plot_pairing_violin),
    ]


_init_commands()


@cli.command(":document")
def document(
    x: int = CommonArgs.documentation_level,
    to: str = CommonArgs.documentation_out,
    style: str = CommonArgs.documentation_format,
    search: bool = Opt.flag(r"Only include specific-search commands.", hidden=True),
    main: bool = Opt.flag(r"Only include main commands.", hidden=True),
    hidden: bool = Opt.flag(r"""Show hidden commands.""", hidden=True),
    replace: bool = CommonArgs.replace,
    log: typing.Optional[Path] = CommonArgs.log_path,
    quiet: bool = CommonArgs.quiet,
    verbose: bool = CommonArgs.verbose,
):
    """
    Output information on available commands.
    """
    MANDOS_SETUP(log, quiet, verbose)
    if main and search:
        fail("Cannot provide both --only-main and --only-search")
    default = Path("mandos-commands" + MANDOS_SETTINGS.default_table_suffix)
    to = MiscUtils.adjust_filename(Path(to), default, replace)
    documenter = Documenter(cli.registered_commands, main, search, hidden)
    documenter.document(level=x, to=to, style=style, replace=replace)


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
