"""
Command-line interface for mandos.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import typer

from mandos.analysis import SimilarityDf
from mandos.analysis.concordance import ConcordanceCalculation, TauConcordanceCalculator
from mandos.analysis.distances import JPrimeMatrixCalculator, MatrixCalculation
from mandos.analysis.filtration import Filtration
from mandos.analysis.enrichment import EnrichmentAlg, EnrichmentCalculation, ScoreDf
from mandos.analysis.reification import Reifier
from mandos.entries.common_args import Arg
from mandos.entries.common_args import CommonArgs as Ca
from mandos.entries.common_args import Opt
from mandos.entries.multi_searches import MultiSearch
from mandos.entries.searcher import SearcherUtils
from mandos.model import START_TIMESTAMP, MiscUtils
from mandos.model.hits import HitFrame
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy_caches import TaxonomyFactories


class MiscCommands:
    @staticmethod
    def search(
        path: Path = Ca.compounds,
        config: Path = Arg.in_file(
            r"""
            A TOML config file. See docs.
            """
        ),
        out_dir: Path = Ca.out_dir,
    ) -> None:
        """
        Run multiple searches.
        """
        MultiSearch.build(path, out_dir, config).run()

    @staticmethod
    def serve(
        port: int = Opt.val("A port to serve on", default=1540),
        db: str = Opt.val("The name of the MySQL database", default="mandos"),
    ) -> None:
        r"""
        Start the REST server.

        The connection information is stored in your global settings file.
        """

    @staticmethod
    def deposit(
        path: Path = Ca.file_input,
        db: str = Opt.val("The name of the MySQL database", default="mandos"),
        host: str = Opt.val(
            "Database hostname (ignored if ``--socket`` is passed", default="127.0.0.1"
        ),
        socket: Optional[str] = Opt.val("Path to a Unix socket (if set, ``--host`` is ignored)"),
        user: Optional[str] = Opt.val("Database username (empty if not set)"),
        password: Optional[str] = Opt.val("Database password (empty if not set)"),
    ) -> None:
        r"""
        Export to a relational database.

        Saves data from Mandos search commands to a database for serving via REST.

        See also: ``:serve``.
        """

    @staticmethod
    def find(
        path: Path = Ca.compounds,
        to: Path = Opt.out_path(
            rf"""
            A table of compounds and their matching database IDs will be written here.

            {Ca.output_formats}

            [default: <path>-ids-<start-time>.{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        replace: bool = Ca.replace,
        pubchem: bool = typer.Option(True, help="Download data from PubChem"),
        chembl: bool = typer.Option(True, help="Download data from ChEMBL"),
        hmdb: bool = typer.Option(True, help="Download data from HMDB"),
        complain: bool = Opt.flag("Log each time a compound is not found"),
    ) -> None:
        r"""
        Fetches and caches compound data.

        Useful to check what you can see before running a search.
        """
        default = str(path) + "-ids" + START_TIMESTAMP + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        inchikeys = SearcherUtils.read(path)
        df = SearcherUtils.dl(
            inchikeys, pubchem=pubchem, chembl=chembl, hmdb=hmdb, complain=complain
        )
        df.write_file(to)
        typer.echo(f"Wrote to {to}")

    @staticmethod
    def build_taxonomy(
        taxa: str = Ca.taxa,
        forbid: str = Opt.val(
            r"""Exclude descendents of these taxa IDs or names (comma-separated).""", default=""
        ),
        to: Path = typer.Option(
            None,
            help=rf"""
            Where to export a table of the taxonomy.

            {Ca.output_formats}

            [default: ./<taxa>-<datetime>.{MANDOS_SETTINGS.default_table_suffix}]
            """,
        ),
        replace: bool = Ca.replace,
    ):
        """
        Exports a taxonomic tree to a table.

        Writes a taxonomy of given taxa and their descendants to a table.
        """
        concat = taxa + "-" + forbid
        taxa = Ca.parse_taxa(taxa)
        forbid = Ca.parse_taxa(forbid)
        default = concat + "-" + START_TIMESTAMP + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        my_tax = TaxonomyFactories.get_smart_taxonomy(taxa, forbid)
        my_tax = my_tax.to_df()
        to.parent.mkdir(exist_ok=True, parents=True)
        my_tax.write_file(to)

    @staticmethod
    def dl_tax(
        taxon: int = Arg.x("The **ID** of the UniProt taxon"),
    ) -> None:
        """
        Preps a new taxonomy file for use in mandos.
        Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
        Otherwise, downloads a tab-separated file from UniProt.
        (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
        Then applies fixes and reduces the file size, creating a new file alongside.
        Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.
        """
        TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(taxon)

    @staticmethod
    def concat(
        path: Path = Ca.input_dir,
        to: Optional[Path] = Ca.to_single,
        replace: bool = Ca.replace,
    ) -> None:
        r"""
        Concatenates Mandos annotation files into one.

        Note that ``:search`` automatically performs this;
        this is needed only if you want to combine results from multiple independent searches.
        """
        default = path / ("concat" + MANDOS_SETTINGS.default_table_suffix)
        to = MiscUtils.adjust_filename(to, default, replace)
        for found in path.iterdir():
            pass

    @staticmethod
    def filter_taxa(
        path: Path = Ca.file_input,
        to: Path = Opt.out_path(
            f"""
            An output path (file or directory).

            {Ca.output_formats}

            [default: <path>/<filters>.feather]
            """
        ),
        allow: str = Ca.taxa,
        forbid: str = Ca.taxa,
        replace: bool = Ca.replace,
    ):
        """
        Filter by taxa.

        You can include any number of taxa to allow and any number to forbid.
        All descendents of the specified taxa are used.
        Taxa will be excluded if they fall under both.

        Note that the <path> argument *could* not be from Mandos.
        All that is required is a column called ``taxon``, ``taxon_id``, or ``taxon_name``.

        See also: :filter, which is more general.
        """
        concat = allow + "-" + forbid
        allow = Ca.parse_taxa(allow)
        forbid = Ca.parse_taxa(forbid)
        if to is None:
            to = path.parent / (concat + MANDOS_SETTINGS.default_table_suffix)
        default = str(path) + "-filter-taxa-" + concat + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        df = HitFrame.read_file(path)
        my_tax = TaxonomyFactories.get_smart_taxonomy(allow, forbid)
        cols = [c for c in ["taxon", "taxon_id", "taxon_name"] if c in df.columns]

        def permit(row) -> bool:
            return any((my_tax.get_by_id_or_name(getattr(row, c)) is not None for c in cols))

        df = df[df.apply(permit)]
        df.write_file(to)

    @staticmethod
    def filter(
        path: Path = Ca.to_single,
        by: Optional[Path] = Arg.in_file(
            """
            The path to a TOML (.toml) file containing filters.

            The file contains a list of ``mandos.filter`` keys,
            each containing an expression on a single column.
            This is only meant for simple, quick-and-dirty filtration.

            See the docs for more info.
            """
        ),
        to: Optional[Path] = Ca.to_single,
        replace: bool = Ca.replace,
    ) -> None:
        """
        Filters by simple expressions.
        """
        if to is None:
            to = path.parent / (by.stem + MANDOS_SETTINGS.default_table_suffix)
        default = str(path) + "-filter-" + by.stem + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        df = HitFrame.read_file(path)
        Filtration.from_file(by).apply(df).write_file(to)

    @staticmethod
    def state(
        path: Path = Ca.file_input,
        to: Optional[Path] = Opt.out_path(
            """
            The path to the output file.

            Valid formats and filename suffixes are .nt and .txt with an optional .gz, .zip, or .xz.
            If only a filename suffix is provided, will use that suffix with the default directory.
            If no suffix is provided, will interpret the path as a directory but use the default filename.
            Will fail if the file exists and ``--replace`` is not set.

            [default: <path>-statements.nt]
        """
        ),
        replace: bool = Ca.replace,
    ) -> None:
        """
        Outputs simple N-triples statements.

        Each statement is of this form, where the InChI Key refers to the input data:

        `"InChI Key" "predicate" "object" .`
        """
        default = str(path) + "-statements.nt"
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
            The path to the output file.

            The filename suffix should be either .nt (N-triples) or .ttl (Turtle),
            with an optional .gz, .zip, or .xz.
            If only a filename suffix is provided, will use that suffix with the default directory.
            If no suffix is provided, will interpret the path as a directory but use the default filename.
            Will fail if the file exists and ``--replace`` is not set.

            [default: <path>-reified.nt]
        """
        ),
        replace: bool = Ca.replace,
    ) -> None:
        """
        Outputs reified semantic triples.
        """
        default = str(path) + "-reified.nt"
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
            The path to the output file.

            {Ca.output_formats}

            [default: <path.parent>/export{MANDOS_SETTINGS.default_table_suffix}]
        """
        ),
        replace: bool = Ca.replace,
    ) -> None:
        """
        Copies and/or converts annotation files.

        Example: ``:export:copy --to .snappy`` to highly compress a data set.
        """

        default = str(path.parent / MANDOS_SETTINGS.default_table_suffix)
        to = MiscUtils.adjust_filename(to, default, replace)

    @staticmethod
    def alpha(
        path: Path = Ca.file_input,
        scores: Path = Ca.alpha_input,
        to: Optional[Path] = Ca.alpha_to,
        algorithm: Optional[str] = Opt.val(
            rf"""
            Algorithm to use.

            Will be applied to all scores / columns.
            Allowed values:

            {Ca.definition_list({a.name: a.description for a in EnrichmentAlg})}
            """,
            default="alpha",
        ),
        replace: bool = Ca.replace,
    ) -> None:
        """
        Compares annotations to user-supplied values.

        Calculates correlation between provided scores and object/predicate pairs.

        See the docs for more info.
        """
        default = str(path) + "-" + scores.name + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path)
        scores = ScoreDf.read_file(scores)
        calculator = EnrichmentCalculation.create(algorithm)
        df = calculator.calc_many(hits, scores)
        df.write_file(to)

    @staticmethod
    def beta(
        path: Path = Ca.file_input,
        scores: Path = Ca.beta_input,
        how: bool = Opt.val(
            r"""
            Determines whether the resulting rows mark single predicate/object pairs,
            or sets of pairs.

            **If "choose"**, decides whether to use intersection or union based on the search type.
            For example, ``chembl:mechanism`` use the intersection,
            while most others will use the union.

            **If "intersection"**, each compound will contribute to a single row
            for its associated set of pairs.
            For example, a compound annotated for ``increase dopamine`` and ``decrease serotonin``
            increment the count for a single row:
            object ``["dopamine", "serotonin"]`` and predicate ``["increase", "decrease"]``.
            (Double quotes will be escaped.)

            **If "union"**, each compound will contribute to one row per associated pair.
            In the above example, the compound will increment the counts
            of two rows: object=``dopamine`` / predicate=``increase``
            and ``object=serotonin`` and predicate=``decrease``.

            In general, this flag is useful for variables in which:

            - A *set of pairs* best is needed to describe a compound, AND

            - There are likely to be relatively few unique predicate/object pairs.

            For example, binding to a hand-selected list of 20 targets with high confidence
            may allow for multipharmacology. However, co-mentions of genes will likely result
            in a very large number of unique rows.
        """
        ),
        to: Optional[Path] = Ca.beta_to,
        replace: bool = Ca.replace,
    ) -> None:
        """
        Compares annotations for hits and non-hits.

        This is a very simple function.
        For each object/predicate pair, counts the annotations for hits and annotations for non-hits.

        See the docs for more info.
        """
        default = str(path) + "-" + scores.name + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path)
        scores = ScoreDf.read_file(scores)
        # calculator = EnrichmentCalculation.create(algorithm)
        # df = calculator.calc_many(hits, scores)
        # df.write_file(to)

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
        to: Optional[Path] = Opt.out_file(
            rf"""
            The path to a similarity matrix file.

            {Ca.output_formats}

            [default: <input-path.parent>/<algorithm>-similarity.{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        replace: bool = Ca.replace,
    ) -> None:
        r"""
        Calculates a similarity matrix from annotations.

        The data are output as a dataframe (CSV by default), where rows and columns correspond
        to compounds, and the cell i,j is the overlap J' in annotations between compounds i and j.
        """
        default = path.parent / (algorithm + MANDOS_SETTINGS.default_table_suffix)
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        calculator = MatrixCalculation.create(algorithm)
        matrix = calculator.calc_all(hits)
        matrix.write_file(to)

    @staticmethod
    def tau(
        phi_matrix: Path = Ca.input_matrix,
        psi_matrix: Path = Ca.input_matrix,
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating concordance.

            Currently, only "tau" is supported.
            This calculation is a modified Kendall’s  τ-a, where disconcordant ignores ties.
            See the docs for more info.
            """,
            default="tau",
        ),
        phi: str = Opt.val("A name for phi", default="phi"),
        psi: str = Opt.val("A name for psi", default="psi"),
        seed: int = Ca.seed,
        samples: int = Ca.n_samples,
        to: Optional[Path] = Opt.out_file(
            rf"""
            The path to a dataframe file for output.

            {Ca.output_formats}

            [default: <input-path.parent>/<algorithm>-concordance.{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        replace: bool = Ca.replace,
    ) -> None:
        r"""
        Calculate correlation between matrices.

        Values are calculated over bootstrap, outputting a dataframe (CSV by default).

        Phi is typically a phenotypic matrix, and psi a matrix from Mandos.
        Alternatively, these might be two matrices from Mandos.

        This command is designed to calculate the similarity between compound annotations
        (from Mandos) and some user-input compound–compound similarity matrix.
        (For example, vectors from a high-content cell screen.
        See ``:calc:score`` if you have a single variable,
        such as a hit or lead-like score.
        """
        if to is None:
            to = phi_matrix.parent / (
                psi_matrix.stem + "-" + algorithm + MANDOS_SETTINGS.default_table_suffix
            )
        if to.exists() and not replace:
            raise FileExistsError(f"File {to} already exists")
        phi_matrix = SimilarityDf.read_file(phi_matrix)
        psi_matrix = SimilarityDf.read_file(psi_matrix)
        calculator = ConcordanceCalculation.create(algorithm, phi, psi, samples, seed)
        concordance = calculator.calc(phi_matrix, psi_matrix)
        concordance.write_file(to)

    @staticmethod
    def plot_umap(
        psi_matrix: Path = Ca.input_matrix,
        colors: Optional[Path] = Ca.colors,
        markers: Optional[Path] = Ca.markers,
        color_col: Optional[str] = Ca.color_col,
        marker_col: Optional[str] = Ca.marker_col,
        cols: int = Opt.val("""The number of columns to use (before going down a row)"""),
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plot UMAP of psi matrices.

        The input will probably be calculated from ``:calc:matrix``.

        Will plot each variable (psi) over a grid.
        """

    @staticmethod
    def plot_pairing_scatter(
        path: Path = Ca.input_matrix,
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plots scatter plots of phi against psi.

        Plots scatter plots of (phi, psi) values, sorted by phi values.

        For each unique phi matrix and psi matrix, flattens the matrices and plots
        the flattened (n choose 2 - n) pairs of each jointly, phi mapped to the x-axis
        and psi mapped to the y-axis.

        Will plot each (phi, psi) pair over a grid, one plot per cell:
        One row per phi and one column per psi.
        """

    @staticmethod
    def plot_pairing_violin(
        path: Path = Ca.input_matrix,
        split: bool = Opt.flag(
            r"""
            Split each violin into phi_1 on the left and phi_2 on the right.

            Useful to compare two phi variables. Requires exactly 2.
            """
        ),
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plots violin plots from data generated by ``:calc:matrix-tau``.

        Will plot each (phi, psi) pair over a grid, one row per phi and one column per psi
        (unless ``--split`` is set).
        """

    @staticmethod
    def plot_score_correlation(
        path: Path = Ca.input_matrix,
        to: Optional[Path] = Ca.plot_to,
    ) -> None:
        r"""
        Plots violin plots from data generated by ``:calc:matrix-tau``.

        Will plot (phi, psi) pairs over a grid, one row per phi and one column per psi.
        """


__all__ = ["MiscCommands"]
