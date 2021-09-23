"""
Common argument processing and arguments for Typer.
"""
import os
from typing import Optional, TypeVar

from typeddfs.cli_help import DfCliHelp

from mandos.model.hits import HitFrame
from mandos.entry._arg_utils import Arg, Opt, ArgUtils
from mandos.entry.searchers import InputFrame
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.utils.setup import MandosLogging, MANDOS_SETUP

T = TypeVar("T", covariant=True)
DEF_SUFFIX = MANDOS_SETTINGS.default_table_suffix


class CommonArgs:

    output_formats = fr"""\

        The filename suffix will set the output format (default: {DEF_SUFFIX}).
        The suffix must be one of: .feather; .snappy/.parquet; or
        .csv, .tsv, .tab (with optional .gz/.bz2/.zip/.xz).
        Feather (.feather) and Parquet (.snappy) are recommended.

        If only a filename suffix is provided, only sets the format and suffix.
        If no suffix is provided, interprets that path as a directory and uses Feather.
        Will fail if the file exists, unless `--replace` is passed.
    """

    input_formats = r"""
        The filename extension must be one of: .feather; .snappy/.parquet;
        .csv, .tsv, .tab (with optional .gz/.bz2/.zip/.xz); .xlsx; or .ods.
        Feather (.feather) and Parquet (.snappy) are recommended.
        (.json, .h5, .xls, and others may be accepted but are discouraged.)
    """

    replace: bool = Opt.flag(
        r"""
        Replace output file(s) if they exist.
        """
    )

    skip: bool = Opt.flag(
        """
        Skip any search if the output file exists.

        See also: ``--replace``.
        """
    )

    exclude = Opt.val(
        r"""
        Regex for input filenames to ignore.

        Uses the PyPi package 'regex'.
        """
    )

    stderr: bool = Opt.val(
        rf"""
        How much logging output to show..

        Can be, from least to most verbose: {", ".join(MANDOS_SETUP.LEVELS)}
        (Aliases: {MANDOS_SETUP.ALIASES}.)
        """,
        "--stderr",
        default=MandosLogging.DEFAULT_LEVEL,
    )

    yes: bool = Opt.flag(
        r"""
        Answer yes to all prompts (non-interactive).
        """,
    )

    in_compound_table = Arg.in_file(
        rf"""
        The path to the file listing compounds.

        {input_formats}

        Must contain a column called 'inchikey'. If provided, a 'compound_id' column
        will be copied in the results to facilitate lookups.
        Some searches and commands require a full structure via either "inchi" or "smiles"
        as a column. These will only be used as needed.

        {ArgUtils.df_description(InputFrame)}
        """
    )

    in_annotations_file = Arg.in_file(
        rf"""
        The path to a file output by ``:concat`` or ``:search``.
        """
    )

    out_annotations_file = Opt.out_file(
        rf"""
        Output file containing annotations.

        {output_formats}

        {ArgUtils.df_description(HitFrame)}

        Various columns specific to each search will also be output.
        For example, a taxon name or evidence level.

        [default: <input-path>/{...}{MANDOS_SETTINGS.default_table_suffix}]
        """
    )

    out_misc_dir = Opt.out_dir(
        rf"""
        Choose the output directory.

        [default: .]
        """,
        "--to",
    )

    out_wildcard = Opt.val(
        rf"""
        The output directory.

        Use the format "<path>{os.sep}*<suffix>" to set the output format.
        (e.g. "output/*.csv.gz").
        {output_formats}
        """
    )

    taxa = Opt.val(
        r"""
        The IDs and/or names of UniProt taxa, comma-separated.

        IDs are preferred because they are always unambiguous.
        Taxon scientific names, common names, and mnemonics can be used for vertebrate species.
        To find more, explore the hierarchy under:

        - https://www.uniprot.org/taxonomy/131567 (cellular species)

        - https://www.uniprot.org/taxonomy/10239 (viral species)

        [default: 7742] (Euteleostomi)
        """,
        "--taxa",
        "7742",
        show_default=False,
    )

    in_cache: bool = Opt.flag(
        r"""
        Do not download any data, and fail if needed data is not cached.
        """,
        "--in-cache",
        hidden=True,
    )

    as_of: Optional[str] = Opt.val(
        f"""
        Restrict to data that was cached as of some date and time.

        This option can be useful for reproducibility.
        Note that this should imply that underlying data sources (such as of deposition or publication)
        are restricted by this datetime, but that is not checked.

        Examples:

            - --as-of 2021-10-11T14:12:13Z

            - --as-of 2021-10-11T14:12:13+14:00

            - --as-of "2021-10-11 14:12:13,496,915+14:00"

            - --as-of "2021-10-11 14:12:13-8:00 [America/Los_Angeles]"

        The supported syntax is ``YYYY-mm-dd'T':hh:MM:ss(iii[.iii][.iii)Z``.
        You can use a space instead of 'T' and ',' as a thousands separator.
        A UTC offset is required, even with an IANA zone in brackets.
        """
    )

    log = Opt.val(
        rf"""
        Log to a file as well as stderr.

        The suffix can be .log, .log.gz, .log.zip, .json, .json.gz, or .json.gz.
        Prefix the path with :LEVEL: to control the level for this file (e.g. ``:INFO:out.log``).
        The level can be, from least to most verbose: {", ".join(MANDOS_SETUP.LEVELS)}
        (Aliases: {MANDOS_SETUP.ALIASES}.)
        """,
    )

    no_setup: bool = Opt.flag(
        r"Skip setup, such as configuring logging.",
        "--no-setup",
        hidden=True,
    )


__all__ = ["CommonArgs"]
