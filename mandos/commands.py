"""
Command-line interface for mandos.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, List

import typer
from mandos.entries.searcher import InputFrame

from mandos.entries.api_singletons import Apis

from mandos import logger, MANDOS_SETUP
from mandos.analysis.io_defns import SimilarityDfLongForm, SimilarityDfShortForm
from mandos.analysis.concordance import ConcordanceCalculation
from mandos.analysis.distances import MatrixCalculation
from mandos.analysis.filtration import Filtration
from mandos.analysis.enrichment import EnrichmentCalculation, RealAlg, BoolAlg
from mandos.analysis.io_defns import ScoreDf
from mandos.analysis.prepping import MatrixPrep
from mandos.analysis.projection import UmapCalc
from mandos.analysis.reification import Reifier
from mandos.entries.common_args import Arg, CommonArgs
from mandos.entries.common_args import CommonArgs as Ca
from mandos.entries.common_args import Opt
from mandos.entries.multi_searches import MultiSearch
from mandos.entries.filler import CompoundIdFiller, IdMatchFrame
from mandos.model import START_TIMESTAMP
from mandos.model.utils import MiscUtils
from mandos.model.apis.g2p_api import CachedG2pApi
from mandos.model.hits import HitFrame
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.analysis.projection import UMAP
from mandos.model.rdkit_utils import RdkitUtils, Fingerprint

set_up = MANDOS_SETUP
DEF_SUFFIX = MANDOS_SETTINGS.default_table_suffix

if UMAP is None:
    _umap_params = {}
else:
    _umap_params = {
        k: v
        for k, v in UMAP().get_params(deep=False).items()
        if k not in {"random_state", "metric"}
    }


class MiscCommands:
    @staticmethod
    def search(
        path: Path = Ca.compounds,
        config: Path = Arg.in_file(
            r"""
            TOML config file. See docs.
            """
        ),
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        out_dir: Path = Ca.out_dir,
    ) -> None:
        """
        Run multiple searches.
        """
        set_up(log, quiet, verbose)
        MultiSearch.build(path, out_dir, config).run()

    @staticmethod
    def serve(
        port: int = Opt.val(r"Port to serve on", default=1540),
        db: str = Opt.val("Name of the MySQL database", default="mandos"),
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Start a REST server.

        The connection information is stored in your global settings file.
        """
        set_up(log, quiet, verbose)

    @staticmethod
    def deposit(
        path: Path = Ca.file_input,
        db: str = Opt.val(r"Name of the MySQL database", default="mandos"),
        host: str = Opt.val(
            r"Database hostname (ignored if ``--socket`` is passed", default="127.0.0.1"
        ),
        socket: Optional[str] = Opt.val("Path to a Unix socket (if set, ``--host`` is ignored)"),
        user: Optional[str] = Opt.val("Database username (empty if not set)"),
        password: Optional[str] = Opt.val("Database password (empty if not set)"),
        as_of: Optional[str] = CommonArgs.as_of,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Export to a relational database.

        Saves data from Mandos search commands to a database for serving via REST.

        See also: ``:serve``.
        """
        set_up(log, quiet, verbose)

    @staticmethod
    def fill(
        path: Path = Ca.compounds_to_fill,
        to: Path = Ca.id_table_to,
        no_pubchem: bool = Opt.flag("Do not use PubChem.", "--no-pubchem"),
        no_chembl: bool = Opt.flag("Do not use ChEMBL.", "--no-chembl"),
        replace: bool = Ca.replace,
        log: Optional[Path] = Ca.log_path,
        quiet: bool = Ca.quiet,
        verbose: bool = Ca.verbose,
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
        set_up(log, quiet, verbose)
        default = str(Path(path).with_suffix("")) + "-filled" + "".join(path.suffixes)
        to = MiscUtils.adjust_filename(to, default, replace)
        df = IdMatchFrame.read_file(path)
        df = CompoundIdFiller(chembl=not no_chembl, pubchem=not no_pubchem).fill(df)
        df.write_file(to)

    @staticmethod
    def cache(
        path: Path = Ca.compounds,
        no_pubchem: bool = Opt.flag(r"Do not download data from PubChem", "--no-pubchem"),
        no_chembl: bool = Opt.flag(r"Do not fetch IDs from ChEMBL", "--no_chembl"),
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Fetch and cache compound data.

        Useful to freeze data before running a search.
        """
        set_up(log, quiet, verbose)
        logger.error(f"Not implemented fully yet.")
        df = IdMatchFrame.read_file(path)
        df = CompoundIdFiller(chembl=not no_chembl, pubchem=not no_pubchem).fill(df)
        logger.notice(f"Done caching.")

    @staticmethod
    def build_taxonomy(
        taxa: str = Ca.taxa,
        forbid: str = Opt.val(
            r"""Exclude descendents of these taxa IDs or names (comma-separated).""", default=""
        ),
        to: Path = typer.Option(
            None,
            help=rf"""
            Where to export.

            {Ca.output_formats}

            [default: ./<taxa>-<datetime>.{DEF_SUFFIX}]
            """,
        ),
        replace: bool = Ca.replace,
        in_cache: bool = CommonArgs.in_cache,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ):
        """
        Export a taxonomic tree to a table.

        Writes a taxonomy of given taxa and their descendants to a table.
        """
        set_up(log, quiet, verbose)
        concat = taxa + "-" + forbid
        taxa = Ca.parse_taxa(taxa)
        forbid = Ca.parse_taxa(forbid)
        default = concat + "-" + START_TIMESTAMP + DEF_SUFFIX
        to = MiscUtils.adjust_filename(to, default, replace)
        my_tax = TaxonomyFactories.get_smart_taxonomy(taxa, forbid)
        my_tax = my_tax.to_df()
        to.parent.mkdir(exist_ok=True, parents=True)
        my_tax.write_file(to)

    @staticmethod
    def dl_tax(
        taxa: str = Opt.val(
            r"""
            Either "vertebrata", "all", or a comma-separated list of UniProt taxon IDs.

            "all" is only valid when --replace is passed;
            this will regenerate all taxonomy files that are found in the cache.
            """,
            default="",
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
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
        if taxa == "":
            logger.info("No taxa were specified. No data downloaded.")
            return
        if (
            taxa not in ["all", "vertebrata"]
            and not taxa.replace(",", "").replace(" ", "").isdigit()
        ):
            raise ValueError(f"Use either 'all', 'vertebrata', or a UniProt taxon ID")
        if taxa == "all" and not replace:
            raise ValueError(f"Use --replace with taxon 'all'")
        set_up(log, quiet, verbose)
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
    def dl_g2p(
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Caches GuideToPharmacology data.

        With --replace set, will overwrite existing cached data.
        Data will generally be stored under``~/.mandos/g2p/``.
        """
        set_up(log, quiet, verbose)
        api = CachedG2pApi(MANDOS_SETTINGS.g2p_cache_path)
        api.download(force=replace)

    @staticmethod
    def clear_cache(
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
        yes: bool = CommonArgs.yes,
    ) -> None:
        """
        Deletes all cached data.
        """
        set_up(log, quiet, verbose)
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
        path: Path = Ca.input_dir,
        to: Optional[Path] = Ca.to_single,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Concatenate Mandos annotation files into one.

        Note that ``:search`` automatically performs this;
        this is needed only if you want to combine results from multiple independent searches.
        """
        set_up(log, quiet, verbose)
        default = path / ("concat" + DEF_SUFFIX)
        to = MiscUtils.adjust_filename(to, default, replace)
        for found in path.iterdir():
            pass

    @staticmethod
    def filter(
        path: Path = Ca.to_single,
        by: Optional[Path] = Arg.in_file(
            r"""
            Path to a TOML (.toml) file containing filters.

            The file contains a list of ``mandos.filter`` keys,
            each containing an expression on a single column.
            This is only meant for simple, quick-and-dirty filtration.

            See the docs for more info.
            """
        ),
        to: Optional[Path] = Ca.to_single,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Filters by simple expressions.
        """
        set_up(log, quiet, verbose)
        default = str(path) + "-filter-" + by.stem + DEF_SUFFIX
        to = MiscUtils.adjust_filename(to, default, replace)
        df = HitFrame.read_file(path)
        Filtration.from_file(by).apply(df).write_file(to)

    @staticmethod
    def state(
        path: Path = Ca.file_input,
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
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Output simple N-triples statements.

        Each statement is of this form, where the InChI Key refers to the input data:

        `"InChI Key" "predicate" "object" .`
        """
        set_up(log, quiet, verbose)
        default = f"{path}-statements.nt"
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        with to.open() as f:
            for hit in hits:
                f.write(hit.to_triple.n_triples)

    @staticmethod
    def reify(
        path: Path = Ca.file_input,
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
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Outputs reified semantic triples.
        """
        set_up(log, quiet, verbose)
        default = f"{path}-reified.nt"
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        with to.open() as f:
            for triple in Reifier().reify(hits):
                f.write(triple.n_triples)

    @staticmethod
    def copy(
        path: Path = Ca.file_input,
        to: Optional[Path] = Opt.out_path(
            rf"""
            Path to the output file.

            {Ca.output_formats}

            [default: <path.parent>/export{DEF_SUFFIX}]
        """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Copies and/or converts annotation files.

        Example: ``:export:copy --to .snappy`` to highly compress a data set.
        """
        set_up(log, quiet, verbose)
        default = path.parent / DEF_SUFFIX
        to = MiscUtils.adjust_filename(to, default, replace)
        df = HitFrame.read_file(path)
        df.write_file(to)

    @staticmethod
    def analyze(
        path: Path = Ca.file_input,
        phi: Path = Ca.input_matrix,
        scores: Path = Ca.alpha_input,
        seed: int = Ca.seed,
        samples: int = Ca.boot,
        to: Optional[Path] = Ca.misc_out_dir,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Shorthand for multiple calculations and plots.

        Generates n-triple statements and reified n-triples.
        Calculates correlation and enrichment using ``scores``,
        psi matrices (one per variable), and concordance between psi and tau matrices (tau).
        Plots UMAP of psi variables, enrichment bar plots, correlation violin plots,
        phi-vs-psi scatter and line plots, and phi-vs-psi (tau) violin plots.
        """

    @staticmethod
    def alpha(
        path: Path = Ca.file_input,
        scores: Path = Ca.alpha_input,
        bool_alg: Optional[str] = Opt.val(
            rf"""
            Algorithm to use for scores starting with 'is_'.

            Allowed values: {Ca.list(BoolAlg)}
            """,
            default="alpha",
        ),
        real_alg: Optional[str] = Opt.val(
            rf"""
            Algorithm to use for scores starting with 'score_'.

            Allowed values: {Ca.list(RealAlg)}
            """,
            default="weighted",
        ),
        on: bool = Ca.on,
        boot: int = Ca.boot,
        seed: int = Ca.seed,
        to: Optional[Path] = Ca.alpha_to,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        """
        Compare annotations to user-supplied values.

        Calculates correlation between provided scores and object/predicate pairs.
        For booleans, compares annotations for hits and non-hits.
        See the docs for more info.
        """
        set_up(log, quiet, verbose)
        default = f"{path}-{scores.name}{DEF_SUFFIX}"
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path)
        scores = ScoreDf.read_file(scores)
        calculator = EnrichmentCalculation(bool_alg, real_alg, boot, seed)
        df = calculator.calculate(hits, scores)
        df.write_file(to)

    @staticmethod
    def psi(
        path: Path = Ca.file_input,
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating similarity between annotation sets.

            Currently, only "j" (J') is supported. Refer to the docs for the equation.
            """,
            default="j",
        ),
        to: Path = Ca.output_matrix,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Calculate a similarity matrix from annotations.

        The data are output as a dataframe (CSV by default), where rows and columns correspond
        to compounds, and the cell i,j is the overlap J' in annotations between compounds i and j.
        """
        set_up(log, quiet, verbose)
        default = path.parent / (algorithm + DEF_SUFFIX)
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        calculator = MatrixCalculation.create(algorithm)
        matrix = calculator.calc_all(hits)
        matrix.write_file(to)

    @staticmethod
    def calc_ecfp_psi(
        path: Path = CommonArgs.compounds,
        radius: int = Opt.val(r"""Radius of the ECFP fingerprint.""", default=4),
        n_bits: int = Opt.val(r"""Number of bits.""", default=2048),
        psi: bool = Opt.flag(
            r"""Use "psi" as the type in the resulting matrix instead of "phi"."""
        ),
        to: Path = Ca.output_matrix,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Compute a similarity matrix from ECFP fingerprints.

        Requires rdkit to be installed.

        This is a bit faster than computing using a search and then calculating with ``:calc:psi``.
        Values range from 0 (no overlap) to 1 (identical).
        The type will be "phi" -- in contrast to using :calc:phi.
        See ``:calc:phi`` for more info.
        This is most useful for comparing a phenotypic phi against pure structural similarity.
        """
        set_up(log, quiet, verbose)
        name = f"ecfp{radius}-n{n_bits}"
        default = path.parent / (name + DEF_SUFFIX)
        to = MiscUtils.adjust_filename(to, default, replace)
        df = InputFrame.read_file(path)
        kind = "psi" if psi else "phi"
        short = MatrixPrep.ecfp_matrix(df, radius, n_bits)
        long_form = MatrixPrep(kind, False, False, False).create({name: short})
        long_form.write_file(to)

    @staticmethod
    def tau(
        phi: Path = Ca.input_matrix,
        psi: Path = Ca.input_matrix,
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating concordance.

            Currently, only "tau" is supported.
            This calculation is a modified Kendall’s  τ-a, where disconcordant ignores ties.
            See the docs for more info.
            """,
            default="tau",
        ),
        seed: int = Ca.seed,
        samples: int = Ca.boot,
        to: Optional[Path] = Opt.out_file(
            rf"""
            The path to a table for output.

            {Ca.output_formats}

            [default: <input-path.parent>/<algorithm>-concordance.{DEF_SUFFIX}]
            """,
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Calculate correlation between matrices.

        Values are calculated over bootstrap, outputting a table.

        Phi is typically a phenotypic matrix, and psi a matrix from Mandos.
        This command is designed to calculate the similarity between compound annotations
        (from Mandos) and some user-input compound–compound similarity matrix.
        (For example, vectors from a high-content cell screen.
        See ``:calc:correlation`` or ``:calc:enrichment`` if you have a single variable,
        such as a hit or lead-like score.
        """
        set_up(log, quiet, verbose)
        default = phi.parent / f"{psi.stem}-{algorithm}{DEF_SUFFIX}"
        to = MiscUtils.adjust_filename(to, default, replace)
        phi = SimilarityDfLongForm.read_file(phi)
        psi = SimilarityDfLongForm.read_file(psi)
        calculator = ConcordanceCalculation.create(algorithm, phi, psi, samples, seed)
        concordance = calculator.calc_all(phi, psi)
        concordance.write_file(to)

    @staticmethod
    def calc_umap(
        psi_matrix: Path = Ca.input_matrix,
        algorithm: str = Opt.val(
            r"""
            Projection algorithm.

            Currently only "umap" is supported.
            """,
            default="umap",
        ),
        seed: str = Opt.val(
            r"""
            Random seed (integer or 'none').

            Setting to 'none' may increase performance.
            """,
            default=0,
        ),
        params: str = Opt.val(
            rf"""
            Parameters fed to the algorithm.

            This is a comma-separated list of key=value pairs.
            For example: ``n_neighbors=4,n_components=12,min_dist=0.8``
            Supports all UMAP parameters except random_state and metric:

            {Ca.definition_list(_umap_params) if UMAP else "<list is unavailable>"}
            """,
            default="",
        ),
        to: Optional[Path] = Ca.project_to,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ) -> None:
        r"""
        Calculate compound UMAP from psi matrices.

        The input should probably be calculated from ``:calc:matrix``.
        Saves a table of the UMAP coordinates.
        """
        if algorithm == "umap" and UMAP is None:
            raise ImportError(f"UMAP is not available")

    @staticmethod
    def prep_phi(
        matrices: List[Path] = Ca.input_matrix_short_form,
        kind: str = Ca.var_type,
        to: Path = Ca.output_matrix,
        replace: bool = Ca.replace,
        normalize: bool = Opt.flag(
            r"""Rescale values to between 0 and 1 by (v-min) / (max-min). (Performed after negation.)"""
        ),
        log10: bool = Opt.val(r"""Rescales values by log10. (Performed after normalization.)"""),
        invert: bool = Opt.val(r"""Multiplies the values by -1. (Performed first.)"""),
        log: Optional[Path] = CommonArgs.log_path,
        quiet: bool = CommonArgs.quiet,
        verbose: bool = CommonArgs.verbose,
    ):
        r"""
        Convert phi matrices to one long-form matrix.

        The keys will be derived from the filenames.
        """
        set_up(log, quiet, verbose)
        default = "."
        if to is None:
            try:
                default = next(iter({mx.parent for mx in matrices}))
            except StopIteration:
                logger.warning(f"Outputting to {default}")
        to = MiscUtils.adjust_filename(to, default, replace)
        long_form = MatrixPrep(kind, normalize, log10, invert).from_files(matrices)
        long_form.write_file(to)

    @staticmethod
    def plot_umap(
        umap_df: Path = Ca.project_input,
        style: Optional[Path] = Ca.style_for_compounds,
        color_col: Optional[str] = Ca.color_col,
        marker_col: Optional[str] = Ca.marker_col,
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plot UMAP, etc. of compounds from psi matrices.

        Will plot one variable (psi) per column.
        """

    @staticmethod
    def plot_score(
        path: Path = Ca.input_correlation,
        kind: str = Ca.plot_kind,
        style: Optional[Path] = Ca.style_for_pairs,
        color_col: Optional[str] = Ca.color_col,
        marker_col: Optional[str] = Ca.marker_col,
        ci: float = Ca.ci,
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plot correlation to scores.

        Visualizes the correlation between predicate/object pairs and user-supplied scores.
        Will output one figure (file) per scoring function.
        Will plot (psi, score-fn) pairs over a grid,
        one row per scoring function and column per psi.
        """

    @staticmethod
    def plot_pairing(
        path: Path = Ca.input_matrix,
        join: Optional[bool] = Opt.flag(
            r"""
            Pool all psi variables into a single column with multiple plots.
            """
        ),
        kind: str = Opt.val(
            r"""
            Either 'points', 'lines', or 'points+lines'.

            - points: Scatter plots of (phi, psi) values.

            - lines: Plot a linear interpolation.

            - ci: Plot a linear interpolation with a confidence band.

            - points+lines: Both 'points' and 'lines'.
            """,
            "--type",
        ),
        ci: float = Ca.ci,
        sort_by: str = Opt.val(
            r"""
            Which axis to sort by: 'phi'/'x' or 'psi'/'y'.

            Sorting by psi values (y-axis) makes it easier to compare psi variables,
            while sorting by phi values (x-axis) makes it easier to compare phi variables.
            """,
            default="psi",
        ),
        style: Optional[Path] = Ca.style_for_psi,
        color_col: Optional[str] = Ca.color_col,
        marker_col: Optional[str] = Ca.marker_col,
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plot line plots of phi against psi.

        Plots scatter plots of (phi, psi) values, sorted by phi values.
        All plots are log/log (all similarity values should be scaled from 0 to 1).

        For each unique phi matrix and psi matrix, flattens the matrices and plots
        the flattened (n choose 2 - n) pairs of each jointly, phi mapped to the y-axis
        and psi mapped to the x-axis.

        Without --split:

        Will show values for all psi variables together.
        If ``--color`` is not set, will choose a palette.
        Works best with ``--type lines``.

        With --split:

        Will plot each (phi, psi) pair over a grid, one plot per cell:
        One row per phi and one column per psi.
        """

    @staticmethod
    def plot_pairing_violin(
        path: Path = Ca.input_matrix,
        split: bool = Opt.flag(
            r"""
            Split each violin into phi #1 on the left and phi #2 on the right.

            Useful to compare two phi variables. Requires exactly 2.
            """
        ),
        style: Optional[Path] = Ca.style_for_psi,
        color_col: Optional[str] = Ca.color_col,
        marker_col: Optional[str] = Ca.marker_col,
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plot violin plots from tau values.

        The input data should be generated by ``:calc:phi-vs-psi.tau``.

        Will plot each (phi, psi) pair over a grid, one row per phi and one column per psi
        (unless ``--split`` is set).
        """


__all__ = ["MiscCommands"]
