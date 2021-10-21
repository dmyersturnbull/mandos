"""
Common argument processing and arguments for Typer.
"""
import os
from typing import Optional, TypeVar

import decorateme
from pocketutils.misc.fancy_loguru import FancyLoguruDefaults
from typeddfs.cli_help import DfCliHelp

from mandos.entry.tools.searchers import InputCompoundsDf
from mandos.entry.utils._arg_utils import Arg, Opt
from mandos.model.hit_dfs import HitDf
from mandos.model.settings import SETTINGS

T = TypeVar("T", covariant=True)
DEF_SUFFIX = SETTINGS.table_suffix
nl = "\n\n"


@decorateme.auto_utils()
class CommonArgs:

    replace: bool = Opt.flag(
        r"""
        Replace output file(s) if they exist.
        """
    )

    proceed: bool = Opt.flag(
        r"""
        Continue partially completed results.
        """
    )

    skip: bool = Opt.flag(
        """
        Skip output file(s) that exist.
        """
    )

    exclude = Opt.val(
        r"""
        Regex for input filenames to ignore.
        """
    )

    yes: bool = Opt.flag(
        r"""
        Auto-answer yes to all prompts.
        """,
    )

    stderr: bool = Opt.val(
        rf"""
        How much logging output to show.

        Choices, from least to most verbose: {", ".join(FancyLoguruDefaults.levels_extended)}
        (Aliases: {FancyLoguruDefaults.aliases}.)
        """,
        "--stderr",
        default=FancyLoguruDefaults.level,
    )

    log = Opt.val(
        rf"""
        Log to a file (along with stderr).

        The suffix can be .log, .log.gz, .log.zip, .json, .json.gz, or .json.gz.
        Prefix with :LEVEL: to control the level for this file (e.g. ":INFO:out.log").
        The level can be, from least to most verbose: {", ".join(FancyLoguruDefaults.levels_extended)}
        (Aliases: {FancyLoguruDefaults.aliases}.)
        """,
    )

    in_compound_table = Arg.in_file(
        rf"""
        {DfCliHelp.help(InputCompoundsDf).get_short_text(nl=nl)}

        If provided, "compound_id"
        will be copied in the results to facilitate lookups.
        Some commands require "inchi" or "smiles".
        """,
    )

    in_annotations_file = Arg.in_file(
        rf"""
        A file from ``:concat`` or ``:search``.
        """
    )

    out_annotations_file = Opt.out_file(
        rf"""
        Output file containing annotations.

        {DfCliHelp.help(HitDf).get_short_text(nl=nl)}

        [default: <input-path>/{...}{SETTINGS.table_suffix}]
        """
    )

    out_wildcard = Opt.val(
        rf"""
        The output directory.

        Use "<path>{os.sep}*<suffix>" to set the output format.
        (e.g. "output/*.csv.gz").
        Permitted suffixes: {DfCliHelp.list_formats().get_short_text()}
        """
    )

    taxa = Opt.val(
        r"""
        UniProt ancestor taxa, comma-separated.

        Scientific names, common names, and mnemonics can be used for vertebrate species.
        IDs are preferred. To exclude a subtree, prefix with '-'.
        If including multiple non-vertebrate taxa, consider including the common ancestor
        by appending ":ancestor" with its ID to improve performance.
        These aliases are accepted: "all", "viral", "cellular".
        Case-insensitive.

        Examples:

        - mammalia,-rodentia,-homo sapiens (mammals except rodents and humans)

        - cyanobacteria,fibrobacteres,acidobacteria:2
          (various bacteria, specifying the ancestor (all bacteria))

        [default: 7742] (euteleostomi)
        """,
        "7742",
        show_default=False,
    )

    in_cache: bool = Opt.flag(
        r"""
        Never download; fail if needed data is not cached.
        """,
        "--in-cache",
        hidden=True,
    )

    as_of: Optional[str] = Opt.val(
        f"""
        Restrict to data cached before some datetime.

        Can be useful for reproducibility.

        Examples:

            - --as-of 2021-10-11T14:12:13Z

            - --as-of 2021-10-11T14:12:13+14:00

            - --as-of "2021-10-11 14:12:13,496,915+14:00"

            - --as-of "2021-10-11 14:12:13-8:00 [America/Los_Angeles]"

        The supported syntax is "YYYY-mm-dd'T':hh:MM:ss(iii[.iii][.iii)Z".
        You can use a space instead of 'T' and ',' as a thousands separator.
        If provided, the IANA zone (e.g. "America/Los_Angeles") is only for documentation.
        """
    )


__all__ = ["CommonArgs"]
