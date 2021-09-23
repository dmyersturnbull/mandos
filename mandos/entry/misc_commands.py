"""
Command-line interface for mandos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import regex
import typer
from pocketutils.core.exceptions import BadCommandError, XValueError
from typeddfs import FileFormat

from mandos.model.taxonomy import TaxonomyDf

from mandos.entry._entry_utils import EntryUtils
from mandos.entry.docs import Documenter

from mandos.model.utils.setup import logger
from mandos.entry.searchers import InputFrame
from mandos.model.utils.setup import MANDOS_SETUP
from typeddfs.utils import Utils as TypedDfsUtils
from mandos.analysis.filtration import Filtration
from mandos.analysis.reification import Reifier
from mandos.entry._common_args import CommonArgs
from mandos.entry._arg_utils import Arg, Opt, ArgUtils
from mandos.entry._common_args import CommonArgs as Ca
from mandos.entry.multi_searches import MultiSearch, SearchExplainDf
from mandos.entry.fillers import CompoundIdFiller, IdMatchFrame
from mandos.model.utils.resources import MandosResources
from mandos.model.apis.g2p_api import CachingG2pApi
from mandos.model.hits import HitFrame
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy_caches import TaxonomyFactories

DEF_SUFFIX = MANDOS_SETTINGS.default_table_suffix


class _InsertedCommandListSingleton:
    commands = None


class MiscCommands:
    @staticmethod
    def list_default_settings(
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
    ):
        """
        Write the default settings to stdout.
        """
        MANDOS_SETUP(log, stderr)
        for k, v in MANDOS_SETTINGS.defaults().items():
            typer.echo(f"{k} = {v}")

    @staticmethod
    def document(
        to: Path = Opt.out_file(
            r"""
            The path to write command documentation to.

            The filename can end with .txt with optional compression (e.g. .txt.gz)
            for formatted text output alongside --format.

            Can can also use any table format: .feather; .snappy/.parquet;
            or .csv, .tsv, .tab, .json, .flexwf (with optional .gz/.bz2/.zip/.xz).

            [default: "commands-level<level>.txt"]
            """
        ),
        style: str = Opt.val(
            rf"""
            The format for formatted text output.

            This is ignored if --to is not a .txt file (or .txt.gz, etc.).
            The choices are: "table", "document", {", ".join(TypedDfsUtils.table_formats())}.

            "table" is a special style that saves in any machine-readable table format, such
            as Feather or Parquet (determined by --to).

            "document" is a special style that emits non-table-like flat text.
            """,
            "--style",
            default="table",
        ),
        width: int = Opt.val(
            r"""
            Max number of characters for a cell.

            After that, the text is wrapped.
            Only applies when writing formatted text (.txt, etc.).

            [default: 40 if level > 1; 100 otherwise]
            """,
            default=None,
            show_default=False,
        ),
        level: int = Opt.val(
            r"""
            The amount of detail to output.

            - 1 : show a 1-line description

            - 2 : Show a 1-line description, plus parameter names

            - 3 : Show the full description, plus parameter names, types, and 1-line descriptions

            - 4 : Show the full description, plus parameter names types, and full descriptions

            - 5 : Same as 4, but enable --hidden and --common
            """,
            default=4,
            min=1,
            max=5,
        ),
        main_only: bool = Opt.flag(r"Only include main commands."),
        search_only: bool = Opt.flag(r"Only include search commands."),
        hidden: bool = Opt.flag(r"Show hidden commands."),
        common: bool = Opt.flag(
            r"""
            Show common arguments and options.

            Normally --log, --quiet, and --verbose are excluded,
            along with path, --key, --to, --as-of for searches,
            and the hidden flags for searches --check and --no-setup.
            """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
    ):
        r"""
        Write documentation on commands to a file.
        """
        MANDOS_SETUP(log, stderr)
        if level == 5:
            hidden = common = True
        if width is None and level == 1:
            width = 100
        elif width is None:
            width = 40
        if width == 0:
            width = 9223372036854775807
        default = f"commands-level{level}.txt"
        to = EntryUtils.adjust_filename(to, default, replace)
        doc = Documenter(
            level=level,
            main=main_only,
            search=search_only,
            hidden=hidden,
            common=common,
            width=width,
        )
        doc.document(_InsertedCommandListSingleton.commands, to, style)

    @staticmethod
    def search(
        path: Path = Ca.in_compound_table,
        config: Path = Arg.in_file(
            r"""
            TOML config file. See docs.
            """
        ),
        to: Path = Ca.out_wildcard,
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
        replace: bool = Opt.flag(r"""Overwrite files if they exist."""),
    ) -> None:
        r"""
        Run multiple searches.
        """
        MANDOS_SETUP(log, stderr)
        default = "search-" + MandosResources.start_timestamp_filesys
        out_dir, suffix = EntryUtils.adjust_dir_name(to, default)
        if config is None:
            raise BadCommandError("Specify config")
        logger.notice(f"Will write as {suffix} to {out_dir}")
        MultiSearch.build(path, out_dir, suffix, config, replace, log).run()

    @staticmethod
    def detail_search(
        config: Path = Arg.in_file(
            r"""
            TOML config file. See docs.
            """
        ),
        to: Path = Opt.out_path(
            rf"""
            Write the table here.

            {Ca.output_formats}

            {ArgUtils.df_description(SearchExplainDf)}

            [default: <config>-details{DEF_SUFFIX}]
            """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = Ca.log,
        stderr: str = CommonArgs.stderr,
    ) -> None:
        r"""
        Write details about a search (:search).
        """
        MANDOS_SETUP(log, stderr)
        to = EntryUtils.adjust_filename(
            to, config.parent / (config.name + f"-details{DEF_SUFFIX}"), replace
        )
        search = MultiSearch.build(Path("."), Path("."), config)
        df = search.to_table()
        df.write_file(to)
        logger.notice(f"Wrote search details to {to}")

    @staticmethod
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
        MANDOS_SETUP(log, stderr)

    @staticmethod
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
        MANDOS_SETUP(log, stderr)

    @staticmethod
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
        MANDOS_SETUP(log, stderr)

    @staticmethod
    def fill(
        path: Path = Arg.in_file(
            rf"""
            The path to the file listing compounds by various IDs.

            {Ca.input_formats}

            Can use columns called 'inchikey', 'chembl_id', and 'pubchem_id'.
            Other columns are permitted but will not be used.

            {ArgUtils.df_description(InputFrame)}
            """,
        ),
        to: Path = Opt.out_path(
            rf"""
            A table of compounds and their database IDs will be written here.

            {Ca.output_formats}

            {ArgUtils.df_description(IdMatchFrame)}

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
        MANDOS_SETUP(log, stderr)
        default = str(Path(path).with_suffix("")) + "-filled" + "".join(path.suffixes)
        to = EntryUtils.adjust_filename(to, default, replace)
        df = IdMatchFrame.read_file(path)
        df = CompoundIdFiller(chembl=not no_chembl, pubchem=not no_pubchem).fill(df)
        df.write_file(to)

    @staticmethod
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
        MANDOS_SETUP(log, stderr)
        logger.error(f"Not implemented fully yet.")
        df = IdMatchFrame.read_file(path)
        df = CompoundIdFiller(chembl=not no_chembl, pubchem=not no_pubchem).fill(df)
        logger.notice(f"Done caching.")

    @staticmethod
    def export_taxa(
        taxa: str = Ca.taxa,
        forbid: str = Opt.val(
            r"""Exclude descendents of these taxa IDs or names (comma-separated).""", default=""
        ),
        to: Path = typer.Option(
            None,
            help=rf"""
            Where to export.

            {Ca.output_formats}

            {ArgUtils.df_description(TaxonomyDf)}

            [default: ./<taxa>-<datetime>{DEF_SUFFIX}]
            """,
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
        MANDOS_SETUP(log, stderr)
        concat = taxa + "-" + forbid
        taxa = ArgUtils.parse_taxa(taxa)
        forbid = ArgUtils.parse_taxa(forbid)
        default = concat + "-" + MandosResources.start_timestamp_filesys + DEF_SUFFIX
        to = EntryUtils.adjust_filename(to, default, replace)
        my_tax = TaxonomyFactories.get_smart_taxonomy(taxa, forbid)
        my_tax = my_tax.to_df()
        my_tax.write_file(to, mkdirs=True)

    @staticmethod
    def cache_taxa(
        taxa: str = Opt.val(
            r"""
            Either "vertebrata", "all", or a comma-separated list of UniProt taxon IDs.

            "all" is only valid when --replace is passed;
            this will regenerate all taxonomy files that are found in the cache.
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
        MANDOS_SETUP(log, stderr)
        if taxa == "":
            logger.info("No taxa were specified. No data downloaded.")
            return
        if (
            taxa not in ["all", "vertebrata"]
            and not taxa.replace(",", "").replace(" ", "").isdigit()
        ):
            raise XValueError(f"Use either 'all', 'vertebrata', or a UniProt taxon ID")
        if taxa == "all" and not replace:
            raise XValueError(f"Use --replace with taxon 'all'")
        factory = TaxonomyFactories.from_uniprot()
        if taxa == "all" and replace:
            listed = TaxonomyFactories.list_cached_files()
            for p in listed.values():
                p.unlink()
            factory.rebuild_vertebrata()
            for t in listed.keys():
                factory.load_dl(t)
        elif taxa == "vertebrata" and (replace or not factory.resolve_path(7742).exists()):
            factory.rebuild_vertebrata()
        elif taxa == "vertebrata":
            factory.load_vertebrate(7742)  # should usually do nothing
        else:
            for taxon in [int(t.strip()) for t in taxa.split(",")]:
                factory.delete_exact(taxon)

    @staticmethod
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
        MANDOS_SETUP(log, stderr)
        api = CachingG2pApi(MANDOS_SETTINGS.g2p_cache_path)
        api.download(force=replace)

    @staticmethod
    def cache_clear(
        log: Optional[Path] = CommonArgs.log,
        stderr: str = CommonArgs.stderr,
        yes: bool = CommonArgs.yes,
    ) -> None:
        """
        Deletes all cached data.
        """
        MANDOS_SETUP(log, stderr)
        typer.echo(f"Will recursively delete all of these paths:")
        for p in MANDOS_SETTINGS.all_cache_paths:
            typer.echo(f"    {p}")
        if not yes:
            typer.confirm("Delete?", abort=True)
        for p in MANDOS_SETTINGS.all_cache_paths:
            p.unlink(missing_ok=True)
        logger.notice("Deleted all cached data")

    @staticmethod
    def concat(
        path: Path = Arg.in_dir(
            rf"""
            Directory containing results from a mandos search.

            {Ca.input_formats}
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
        MANDOS_SETUP(log, stderr)
        default = path / ("concat" + DEF_SUFFIX)
        to = EntryUtils.adjust_filename(to, default, replace)
        for found in path.iterdir():
            pass

    @staticmethod
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
        MANDOS_SETUP(log, stderr)
        default = str(path) + "-filter-" + by.stem + DEF_SUFFIX
        to = EntryUtils.adjust_filename(to, default, replace)
        df = HitFrame.read_file(path)
        Filtration.from_file(by).apply(df).write_file(to)

    @staticmethod
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
        MANDOS_SETUP(log, stderr)
        default = f"{path}-statements.nt"
        to = EntryUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        with to.open() as f:
            for hit in hits:
                f.write(hit.to_triple.n_triples)

    @staticmethod
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
        MANDOS_SETUP(log, stderr)
        default = f"{path}-reified.nt"
        to = EntryUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        with to.open() as f:
            for triple in Reifier().reify(hits):
                f.write(triple.n_triples)

    @staticmethod
    def export_copy(
        path: Path = Ca.in_annotations_file,
        to: Optional[Path] = Opt.out_path(
            rf"""
            Path to the output file.

            {Ca.output_formats}

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
        MANDOS_SETUP(log, stderr)
        default = path.parent / DEF_SUFFIX
        to = EntryUtils.adjust_filename(to, default, replace)
        df = HitFrame.read_file(path)
        df.write_file(to)


__all__ = ["MiscCommands"]
