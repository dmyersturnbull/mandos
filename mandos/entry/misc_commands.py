"""
Command-line interface for mandos.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import decorateme
import pandas as pd
import typer
from pocketutils.core.chars import Chars
from pocketutils.core.exceptions import XValueError
from pocketutils.tools.string_tools import StringTools
from typeddfs import Checksums, CompressionFormat, FileFormat
from typeddfs.df_errors import InvalidDfError
from typeddfs.typed_dfs import PlainTypedDf, TypedDf
from typeddfs.utils import Utils as TdfUtils
from typeddfs.utils.cli_help import DfCliHelp

from mandos.analysis.filtration import Filtration
from mandos.analysis.io_defns import (
    ConcordanceDf,
    EnrichmentDf,
    PhiPsiSimilarityDfLongForm,
    PsiProjectedDf,
    ScoreDf,
    SimilarityDfLongForm,
)
from mandos.analysis.reification import Reifier
from mandos.entry import entry
from mandos.entry.tools.docs import Documenter
from mandos.entry.tools.fillers import CompoundIdFiller, IdMatchDf
from mandos.entry.tools.multi_searches import MultiSearch, SearchConfigDf
from mandos.entry.tools.searchers import InputCompoundsDf
from mandos.entry.utils._arg_utils import Arg, ArgUtils, EntryUtils, Opt
from mandos.entry.utils._common_args import CommonArgs
from mandos.entry.utils._common_args import CommonArgs as Ca
from mandos.model.apis.g2p_api import CachingG2pApi
from mandos.model.hit_dfs import HitDf
from mandos.model.settings import SETTINGS
from mandos.model.taxonomy import TaxonomyDf
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.model.utils import unlink
from mandos.model.utils.globals import Globals
from mandos.model.utils.setup import LOG_SETUP, logger

DEF_SUFFIX = SETTINGS.table_suffix
nl = "\n\n"


class _InsertedCommandListSingleton:
    commands = None


@decorateme.auto_utils()
class MiscCommands:
    @staticmethod
    @entry()
    def search(
        path: Path = Ca.in_compound_table,
        config: Path = Opt.in_file(
            r"""
            TOML config file. See the docs.
            """,
            default=...,
        ),
        to: Path = Ca.out_wildcard,
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
        replace: bool = Opt.flag(r"""Overwrite completed and partially completed searches."""),
        proceed: bool = Opt.flag(r"""Continue partially completed searches."""),
        check: bool = Opt.flag("Check and write docs file only; do not run"),
    ) -> None:
        r"""
        Run multiple searches.
        """
        LOG_SETUP(log, stderr)
        default = path.parent / ("search-" + Globals.start_time.strftime("%Y-%m-%d"))
        # TODO: , suffixes=FileFormat.from_path
        out_dir, suffix = EntryUtils.adjust_dir_name(to, default)
        logger.notice(f"Will write {suffix} to {out_dir}{os.sep}")
        config_fmt = FileFormat.from_path(config)
        if config_fmt is not FileFormat.toml:
            logger.caution(f"Config format is {config_fmt}, not toml; trying anyway")
        config = SearchConfigDf.read_file(config)
        search = MultiSearch(config, path, out_dir, suffix, replace, proceed, log)
        if not check:
            search.run()

    @staticmethod
    @entry()
    def init(
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ):
        """
        Initializes mandos, creating directories, etc.
        """
        LOG_SETUP(log, stderr)
        Globals.mandos_path.mkdir(exist_ok=True, parents=True)
        typer.echo(f"Mandos home dir is {Globals.mandos_path}")
        if Globals.settings_path.exists():
            typer.echo(f"Settings found at {Globals.settings_path}")
        else:
            typer.echo("No settings file found")
        typer.echo(f"Log level for stderr is level {logger.current_stderr_log_level}")

    @staticmethod
    @entry()
    def list_settings(
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ):
        r"""
        Write the settings to stdout.
        """
        LOG_SETUP(log, stderr)
        defaults = SETTINGS.defaults()
        width = max((len(k) + 2 + len(v) + 1 for k, v in SETTINGS.items()))
        for k, v in SETTINGS.as_dict():
            msg = f"{k} = {v}".ljust(width)
            if v != defaults[k]:
                msg += f" (default: {defaults[k]})"
            typer.echo(msg)

    @staticmethod
    @entry()
    def document(
        to: Path = Opt.out_file(
            rf"""
            The path to write command documentation to.

        `   For machine-readable output: {DfCliHelp.list_formats().get_short_text()}.
            For formatted output: .txt or .rst [{"/".join([str(c) for c in CompressionFormat.list_non_empty()])}

            [default: "commands-level<level>.rst"]
            """
        ),
        style: str = Opt.val(
            rf"""
            The format for formatted text output.

            Use "table" for machine-readable output, "docs" for long-form reStructuredText,
            or {TdfUtils.join_to_str(TdfUtils.table_formats(), last="or")}
            """,
            "--style",
            default="docs",
        ),
        width: int = Opt.val(
            r"""
            Max number of characters for a cell before wrap.

            [default: 0 (none) for machine-readable; 100 for formatted]
            """,
            default=None,
            show_default=False,
        ),
        level: int = Opt.val(
            r"""
            The amount of detail to output.
            (1): 1-line description
            (2): + params
            (3) + full description
            (4) + param 1-line descriptions
            (5) + param full descriptions
            (6) + --hidden --common
            """,
            default=3,
            min=1,
            max=6,
        ),
        no_main: bool = Opt.flag(r"Exclude main commands."),
        no_search: bool = Opt.flag(r"Exclude search commands."),
        hidden: bool = Opt.flag(r"Show hidden commands."),
        common: bool = Opt.flag(
            r"""
            Show common arguments and options.

            Includes --log and --stderr, along with path, --key, --to, etc. for searches.
            """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
    ):
        r"""
        Write documentation on commands to a file.
        """
        LOG_SETUP(log, stderr)
        if level == 5:
            hidden = common = True
        if width is None and style != "table":
            width = 100
        elif width == 0:
            width = None
        default = f"commands-level{level}.rst"
        to = EntryUtils.adjust_filename(to, default, replace=replace)
        Documenter(
            level=level,
            main=not no_main,
            search=not no_search,
            hidden=hidden,
            common=common,
            width=width,
        ).document(_InsertedCommandListSingleton.commands, to, style)

    @staticmethod
    @entry()
    def fill(
        path: Path = Arg.in_file(
            rf"""
            {DfCliHelp.help(InputCompoundsDf).get_short_text(nl=nl)}
            """,
        ),
        to: Path = Opt.out_path(
            rf"""
            {DfCliHelp.help(IdMatchDf).get_short_text(nl=nl)}

            [default: <path>-ids-<start-time>{DEF_SUFFIX}]
            """
        ),
        no_pubchem: bool = Opt.flag("Do not use PubChem.", "--no-pubchem"),
        no_chembl: bool = Opt.flag("Do not use ChEMBL.", "--no-chembl"),
        replace: bool = Ca.replace,
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Fill in missing IDs from existing compound data.

        The idea is to find a ChEMBL ID, a PubChem ID, and parent-compound InChI/InChI Key.
        Useful to check compound/ID associations before running a search.

        To be filled, each row must should have a non-null value for
        "inchikey", "chembl_id", and/or "pubchem_id".
        "inchi" will be used but not to match to PubChem and ChEMBL.

        No existing columns will be dropped or modified.
        Any conflicting column will be renamed to 'origin_<column>'.
        E.g. 'inchikey' will be renamed to 'origin_inchikey'.
        (Do not include a column beginning with 'origin_').

        Final columns (assuming --no-chembl and --no-pubchem) will include:
        inchikey, inchi, pubchem_id, chembl_id, pubchem_inch, chembl_inchi,
        pubchem_inchikey, and chembl_inchikey.
        The "inchikey" and "inchikey" columns will be the "best" available:
        chembl (preferred), then pubchem, then your source inchikey column.
        In cases where PubChem and ChEMBL differ, an error will be logged.
        You can always check the columns "origin_inchikey" (yours),
        chembl_inchikey, and pubchem_inchikey.

        The steps are:

        - If "chembl_id" or "pubchem_id" is non-null, uses that to find an InChI Key (for each).

        - Otherwise, if only "inchikey" is non-null, uses it to find ChEMBL and PubChem records.

        - Log an error if the inchikeys or inchis differ between PubChem and ChEMBL.

        - Set the final "inchi" and "inchikey" to the best choice,
          falling back to the input inchi and inchikey if they are missing.
        """
        LOG_SETUP(log, stderr)
        default = str(Path(path).with_suffix("")) + "-filled" + "".join(path.suffixes)
        to = EntryUtils.adjust_filename(to, default, replace=replace)
        df = IdMatchDf.read_file(path)
        df = CompoundIdFiller(chembl=not no_chembl, pubchem=not no_pubchem).fill(df)
        df.write_file(to)

    @staticmethod
    @entry()
    def cache_data(
        path: Path = Ca.in_compound_table,
        no_pubchem: bool = Opt.flag(r"Do not download data from PubChem", "--no-pubchem"),
        no_chembl: bool = Opt.flag(r"Do not fetch IDs from ChEMBL", "--no_chembl"),
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Fetch and cache compound data.

        Useful to freeze data before running a search.
        """
        LOG_SETUP(log, stderr)
        df = IdMatchDf.read_file(path)
        CompoundIdFiller(chembl=not no_chembl, pubchem=not no_pubchem).fill(df)
        logger.notice(f"Done caching")

    @staticmethod
    @entry()
    def export_taxa(
        taxa: str = Ca.taxa,
        to: Path = Opt.out_path(
            rf"""
            {DfCliHelp.help(TaxonomyDf).get_short_text(nl=nl)}

            [default: ./<taxa>-<datetime>{DEF_SUFFIX}]
            """
        ),
        replace: bool = Ca.replace,
        in_cache: bool = CommonArgs.in_cache,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ):
        """
        Export a taxonomic tree to a table.

        Writes a taxonomy of given taxa and their descendants to a table.
        """
        LOG_SETUP(log, stderr)
        default = taxa + "-" + Globals.start_timestamp_filesys + DEF_SUFFIX
        to = EntryUtils.adjust_filename(to, default, replace=replace)
        tax = ArgUtils.get_taxonomy(taxa, local_only=in_cache, allow_forbid=False).get
        tax.to_df().write_file(to, mkdirs=True, file_hash=True)

    @staticmethod
    @entry()
    def cache_taxa(
        taxa: str = Opt.val(
            r"""
            Either "@all" or a comma-separated list of UniProt taxon IDs.

            "@all" is only valid when --replace is passed;
            this will regenerate all taxonomy files that are found in the cache.
            Aliases "vertebrata", "cellular", and "viral" are permitted.
            """,
            default="",
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Prep a new taxonomy file for use in mandos.

        With --replace set, will delete any existing file.
        This can be useful to make sure your cached taxonomy is up-to-date before running.

        Downloads and converts a tab-separated file from UniProt.
        (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
        Then applies fixes and reduces the file size, creating a new file alongside.
        Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.
        """
        LOG_SETUP(log, stderr)
        if taxa == "@all" and not replace:
            raise XValueError(f"Use --replace with '@all'")
        # we're good to go:
        factory = TaxonomyFactories.main()
        if taxa == "@all":
            taxa = TaxonomyFactories.list_cached_files().keys()
        else:
            taxa = ArgUtils.parse_taxa_ids(taxa)
        factory.rebuild(taxa, replace=replace)

    @staticmethod
    @entry()
    def cache_g2p(
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Caches GuideToPharmacology data.

        With --replace set, will overwrite existing cached data.
        Data will generally be stored under``~/.mandos/g2p/``.
        """
        LOG_SETUP(log, stderr)
        api = CachingG2pApi(SETTINGS.g2p_cache_path)
        api.download(force=replace)

    @staticmethod
    @entry()
    def cache_clear(
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Deletes all cached data.
        """
        LOG_SETUP(log, stderr)
        paths = ", ".join(
            [str(p.relative_to(SETTINGS.cache_path)) for p in SETTINGS.all_cache_paths]
        )
        logger.notice(f"Will recursively delete: {paths}")
        for p in SETTINGS.all_cache_paths:
            unlink(p, missing_ok=True)
        logger.notice("Deleted all cached data")

    @staticmethod
    @entry()
    def concat(
        path: Path = Arg.in_dir(
            rf"""
            Directory containing results from a mandos search.

            {DfCliHelp.list_formats().get_short_text()}
            """
        ),
        to: Optional[Path] = Ca.out_annotations_file,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Concatenate Mandos annotation files into one.

        Note that ``:search`` automatically performs this;
        this is needed only if you want to combine results from multiple independent searches.
        """
        LOG_SETUP(log, stderr)
        files_ = []
        for file in path.iterdir():
            ff = FileFormat.from_path_or_none(file)
            if ff not in [None, FileFormat.json, FileFormat.ini, FileFormat.toml]:
                files_.append(file)
        logger.notice(f"Looking under {path} (NOT recursive)")
        logger.info(f"Found {len(files_):,} potential input files: {[f.name for f in files_]}")
        files, names, dfs = [], [], []
        for file in files_:
            df: HitDf = HitDf.read_file(file, attrs=True)
            files.append(file)
            names.append(FileFormat.strip(file).name)
            dfs.append(df)
        default = path / (",".join(names) + DEF_SUFFIX)
        to = EntryUtils.adjust_filename(to, default, replace)
        df = HitDf.of(dfs, keys=names)
        logger.notice(f"Concatenated {len(files):,} files")
        for f_, df_ in zip(files, dfs):
            logger.success(f"Included: {f_.name} with {len(df_):,} rows")
        counts = {k: v for k, v in df.group_by("universal_id").count().to_dict() if v > 0}
        if len(counts) > 0:
            logger.error(
                f"There are {len(counts):,} universal IDs with duplicates!"
                + f": {StringTools.join_kv(counts)}"
            )
        logger.notice(f"Wrote {len(df):,} rows to {to}")
        df.write_file(to, mkdirs=True, attrs=True, file_hash=True)

    @staticmethod
    @entry()
    def filter(
        path: Path = Ca.out_annotations_file,
        by: Optional[Path] = Arg.in_file(
            r"""
            Path to a file containing filters.

            See the docs for more info.
            """
        ),
        to: Optional[Path] = Ca.out_annotations_file,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Filters by simple expressions.
        """
        LOG_SETUP(log, stderr)
        default = str(path) + "-filter-" + by.stem + DEF_SUFFIX
        to = EntryUtils.adjust_filename(to, default, replace)
        df = HitDf.read_file(path)
        Filtration.from_file(by).apply(df).write_file(to)

    @staticmethod
    @entry()
    def export_state(
        path: Path = Ca.in_annotations_file,
        to: Optional[Path] = Opt.out_path(
            """
            Path to the output file.

            Valid formats and filename suffixes are .nt and .txt with an optional .gz, .zip, or .xz.
            If only a filename suffix is provided, will use that suffix with the default directory.
            If no suffix is provided, will interpret the path as a directory and use the default filename.
            Will fail if the file exists and ``--replace`` is not set.

            [default: <path>-statements.nt]
        """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Output simple N-triples statements.

        Each statement is of this form, where the InChI Key refers to the input data:

        `"InChI Key" "predicate" "object" .`
        """
        LOG_SETUP(log, stderr)
        default = f"{path}-statements.nt"
        to = EntryUtils.adjust_filename(to, default, replace)
        hits = HitDf.read_file(path).to_hits()
        with to.open() as f:
            for hit in hits:
                f.write(hit.to_triple.n_triples)

    @staticmethod
    @entry()
    def export_reify(
        path: Path = Ca.in_annotations_file,
        to: Optional[Path] = Opt.out_path(
            r"""
            Path to the output file.

            The filename suffix should be either .nt (N-triples) or .ttl (Turtle),
            with an optional .gz, .zip, or .xz.
            If only a filename suffix is provided, will use that suffix with the default directory.
            If no suffix is provided, will interpret the path as a directory but use the default filename.
            Will fail if the file exists and ``--replace`` is not set.

            [default: <path>-reified.nt]
            """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Outputs reified semantic triples.
        """
        LOG_SETUP(log, stderr)
        default = f"{path}-reified.nt"
        to = EntryUtils.adjust_filename(to, default, replace)
        hits = HitDf.read_file(path).to_hits()
        with to.open() as f:
            for triple in Reifier().reify(hits):
                f.write(triple.n_triples)

    @staticmethod
    @entry()
    def export_copy(
        path: Path = Opt.val(
            rf"""
            Path to a CSV-like file corresponding to --what.

            {DfCliHelp.list_formats().get_short_text()}
            """
        ),
        what: str = Opt.val(
            r"""
            The type of data.

            Options: "hits", "compounds", "score", "enrichment",
            "matrix" (long-form similarity), "concordance", "phi-psi",
            "projection", or "data" (arbitrary data).
            """,
            default="hits",
        ),
        to: Optional[Path] = Opt.out_path(
            rf"""
            Path to the output file.

            {DfCliHelp.list_formats().get_short_text()}

            [default: <path.parent>/export{DEF_SUFFIX}]
            """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        """
        Copies and/or converts annotation files.

        Example: ``:export:copy --to .snappy`` to highly compress a data set.
        """
        LOG_SETUP(log, stderr)
        default = path.parent / DEF_SUFFIX
        what = dict(
            compounds=InputCompoundsDf,
            hits=HitDf,
            matrix=SimilarityDfLongForm,
            scores=ScoreDf,
            enrichment=EnrichmentDf,
            phi_psi=PhiPsiSimilarityDfLongForm,
            concordance=ConcordanceDf,
            projection=PsiProjectedDf,
            data=PlainTypedDf,
        )[what.lower().strip().replace("-", "_")]
        to = EntryUtils.adjust_filename(to, default, replace)
        attrs_path = path.parent / (path.name + ".attrs.json")
        hash_path = Checksums().get_filesum_of_file(path)
        attrs, file_hash = attrs_path.exists(), hash_path.exists()
        logger.info(f"Reading attributes: {attrs}")
        logger.info(f"Reading checksum file: {file_hash}")
        df: TypedDf = what.read_file(path, attrs=attrs, file_hash=file_hash)
        df.write_file(to, mkdirs=True, attrs=attrs, file_hash=file_hash)
        logger.notice(f"Exported {path} to {path} ({len(df):,} rows")
        if attrs:
            logger.info(f"Wrote attributes to {attrs_path}")
        if file_hash:
            logger.info(f"Wrote single-file checksum to {hash_path}")

    @staticmethod
    @entry()
    def serve(
        port: int = Opt.val(r"Port to serve on", default=1540),
        db: str = Opt.val("Name of the MySQL database", default="mandos"),
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Start a REST server.

        The connection information is stored in your global settings file.
        """
        LOG_SETUP(log, stderr)

    @staticmethod
    @entry()
    def export_db(
        path: Path = Ca.in_annotations_file,
        db: str = Opt.val(r"Name of the MySQL database", default="mandos"),
        host: str = Opt.val(
            r"Database hostname (ignored if ``--socket`` is passed", default="127.0.0.1"
        ),
        socket: Optional[str] = Opt.val("Path to a Unix socket (if set, ``--host`` is ignored)"),
        user: Optional[str] = Opt.val("Database username (empty if not set)"),
        password: Optional[str] = Opt.val("Database password (empty if not set)"),
        as_of: Optional[str] = CommonArgs.as_of,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Export to a relational database.

        Saves data from Mandos search commands to a database for serving via REST.

        See also: ``:serve``.
        """
        LOG_SETUP(log, stderr)

    @staticmethod
    @entry()
    def init_db(
        db: str = Opt.val(r"Name of the MySQL database", default="mandos"),
        host: str = Opt.val(
            r"Database hostname (ignored if ``--socket`` is passed", default="127.0.0.1"
        ),
        socket: Optional[str] = Opt.val("Path to a Unix socket (if set, ``--host`` is ignored)"),
        user: Optional[str] = Opt.val("Database username (empty if not set)"),
        password: Optional[str] = Opt.val("Database password (empty if not set)"),
        overwrite: bool = Opt.flag(r"Delete the database if it exists"),
        yes: bool = Ca.yes,
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Initialize an empty database.
        """
        LOG_SETUP(log, stderr)


__all__ = ["MiscCommands"]
