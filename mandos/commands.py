"""
Command-line interface for mandos.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import typer

from mandos.analysis import SimilarityDf
from mandos.analysis.concordance import TauConcordanceCalculator
from mandos.analysis.distances import JPrimeMatrixCalculator
from mandos.analysis.filtration import Filtration
from mandos.analysis.reification import ReifiedExporter
from mandos.model import MiscUtils, START_NTP_TIMESTAMP
from mandos.model.hits import HitFrame
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.entries.multi_searches import MultiSearch
from mandos.entries.searcher import SearcherUtils
from mandos.entries.common_args import Arg, Opt, CommonArgs


class MiscCommands:
    @staticmethod
    def search(
        path: Path = CommonArgs.compounds,
        config: Path = Arg.in_file(
            r"""
            A TOML config file. See docs.
            """
        ),
    ) -> None:
        """
        Run multiple searches.
        """
        MultiSearch(path, config).search()

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
        path: Path = CommonArgs.file_input,
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
        path: Path = CommonArgs.compounds,
        to: Path = Opt.out_path(
            rf"""
            A table of compounds and their matching database IDs will be written here.

            {CommonArgs.output_formats}

            [default: <path>-ids-<start-time>.{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        replace: bool = CommonArgs.replace,
        pubchem: bool = typer.Option(True, help="Download data from PubChem"),
        chembl: bool = typer.Option(True, help="Download data from ChEMBL"),
        hmdb: bool = typer.Option(True, help="Download data from HMDB"),
        complain: bool = Opt.flag("Log each time a compound is not found"),
    ) -> None:
        r"""
        Fetches and caches compound data.

        Useful to check what you can see before running a search.
        """
        default = str(path) + "-ids" + START_NTP_TIMESTAMP + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)
        inchikeys = SearcherUtils.read(path)
        df = SearcherUtils.dl(
            inchikeys, pubchem=pubchem, chembl=chembl, hmdb=hmdb, complain=complain
        )
        df.write_file(to)
        typer.echo(f"Wrote to {to}")

    @staticmethod
    def build_taxonomy(
        taxa: str = CommonArgs.taxa,
        forbid: str = Opt.val(
            r"""Exclude descendents of these taxa IDs or names (comma-separated).""", default=""
        ),
        to: Path = typer.Option(
            None,
            help=rf"""
            Where to export a table of the taxonomy.

            {CommonArgs.output_formats}

            [default: ./<taxa>-<datetime>.{MANDOS_SETTINGS.default_table_suffix}]
            """,
        ),
        replace: bool = CommonArgs.replace,
    ):
        """
        Exports a taxonomic tree to a table.

        Writes a taxonomy of given taxa and their descendants to a table.
        """
        concat = taxa + "-" + forbid
        taxa = CommonArgs.parse_taxa(taxa)
        forbid = CommonArgs.parse_taxa(forbid)
        default = concat + "-" + START_NTP_TIMESTAMP + MANDOS_SETTINGS.default_table_suffix
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
        path: Path = CommonArgs.dir_input,
        exclude: Optional[str] = CommonArgs.exclude,
        to: Optional[Path] = CommonArgs.to_single,
        replace: bool = CommonArgs.replace,
    ) -> None:
        r"""
        Concatenates Mandos annotation files into one.

        Note that ``:search`` automatically performs this;
        this is needed only if you want to combine results from multiple independent searches.
        """
        default = path / ("concat" + MANDOS_SETTINGS.default_table_suffix)
        to = MiscUtils.adjust_filename(to, default, replace)
        exclude = re.compile(exclude)
        for found in path.iterdir():
            if exclude.fullmatch(found.name) is None:
                pass

    @staticmethod
    def filter_taxa(
        path: Path = CommonArgs.file_input,
        to: Path = Opt.out_path(
            f"""
            An output path (file or directory).

            {CommonArgs.output_formats}

            [default: <path>/<filters>.feather]
            """
        ),
        allow: str = CommonArgs.taxa,
        forbid: str = CommonArgs.taxa,
        replace: bool = CommonArgs.replace,
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
        allow = CommonArgs.parse_taxa(allow)
        forbid = CommonArgs.parse_taxa(forbid)
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
        path: Path = CommonArgs.to_single,
        by: Optional[Path] = Arg.in_file(
            """
            The path to a TOML (.toml) file containing filters.

            The file contains a list of ``mandos.filter`` keys,
            each containing an expression on a single column.
            This is only meant for simple, quick-and-dirty filtration.

            See the docs for more info.
            """
        ),
        to: Optional[Path] = CommonArgs.to_single,
        replace: bool = CommonArgs.replace,
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
        path: Path = CommonArgs.file_input,
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
        replace: bool = CommonArgs.replace,
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
                f.write(hit.to_triple().n_triples)

    @staticmethod
    def reify(
        path: Path = CommonArgs.file_input,
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
        replace: bool = CommonArgs.replace,
    ) -> None:
        """
        Outputs reified semantic triples.
        """
        default = str(path) + "-reified.nt"
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        with to.open() as f:
            for triple in ReifiedExporter().reify(hits):
                f.write(triple.n_triples)

    @staticmethod
    def copy(
        path: Path = CommonArgs.file_input,
        to: Optional[Path] = Opt.out_path(
            rf"""
            The path to the output file.

            {CommonArgs.output_formats}

            [default: <path.parent>/export{MANDOS_SETTINGS.default_table_suffix}]
        """
        ),
        replace: bool = CommonArgs.replace,
    ) -> None:
        """
        Copies and/or converts annotation files.

        Example: ``:export:copy --to .snappy`` to highly compress a data set.
        """

        default = str(path.parent / MANDOS_SETTINGS.default_table_suffix)
        to = MiscUtils.adjust_filename(to, default, replace)

    @staticmethod
    def score(
        path: Path = CommonArgs.file_input,
        scores: Path = Arg.in_file(
            rf"""
            Path to a table containing scores.

            Must contain a column called ``inchikey`` or ``compound_id``
            matching the InChI Keys or compound IDs you provided for the search.

            Any number of scores may be included via columns.
            Each column must match the pattern ``^(?:score)|(?:score[-_ +:].*)$``.
            These values must be floating-point.

            For enrichment, you may also include columns signifying "hit vs. not".
            These columns must match the pattern ``^is[_- +:]$``.
            Values must be boolean (true/false, t/f, yes/no, y/n, 1/0).

            Example columns:

                inchikey    compound_id    is_hit    score_alpha

            {CommonArgs.input_formats}
            """
        ),
        to: Optional[Path] = Opt.out_file(
            rf"""
            Path to write regression info to.

            {CommonArgs.output_formats}

            Columns will correspond to the columns you provided.
            For example, ``r_score_alpha`` for the regression coefficient
            of the score ``alpha``, and ``fold_is_hit`` for the fraction (hits / non-hits) for ``is_hit``.

            [default: <path>-<scores.filename>{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        counts: bool = Opt.flag(
            rf"""Use only the *number* of object/predicate pairs, rather than their weights.""",
        ),
        replace: bool = CommonArgs.replace,
    ) -> None:
        """
        Compares annotations to user-supplied values.

        Calculates correlation between provided scores and object/predicate pairs,
        and/or enrichment of pairs for boolean scores.

        The values used are *weighted object/predicate pairs**,
        unless ``--counts`` is passed.
        See the docs for more info.
        """
        default = str(path) + "-" + scores.name + MANDOS_SETTINGS.default_table_suffix
        to = MiscUtils.adjust_filename(to, default, replace)

    @staticmethod
    def matrix(
        path: Path = CommonArgs.file_input,
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating similarity between annotation sets.

            Currently, only "j" (J') is supported. Refer to the docs for the equation.
            """
        ),
        to: Optional[Path] = Opt.out_file(
            rf"""
            The path to a similarity matrix file.

            {CommonArgs.output_formats}
            .txt is assumed to be whitespace-delimited.

            [default: <input-path.parent>/<algorithm>-similarity.{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        replace: bool = CommonArgs.replace,
    ) -> None:
        r"""
        Calculates a similarity matrix from annotations.

        The data are output as a dataframe (CSV by default), where rows and columns correspond
        to compounds, and the cell i,j is the overlap J' in annotations between compounds i and j.
        """
        default = path.parent / (algorithm + MANDOS_SETTINGS.default_table_suffix)
        to = MiscUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        matrix = JPrimeMatrixCalculator().calc(hits)
        matrix.write_file(to)

    @staticmethod
    def concordance(
        phi: Path = CommonArgs.input_matrix,
        psi: Path = CommonArgs.input_matrix,
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating concordance.

            Currently, only "tau" is supported.
            This calculation is a modified Kendall’s  τ-a, where disconcordant ignores ties.
            See the docs for more info.
            """
        ),
        seed: int = CommonArgs.seed,
        samples: int = CommonArgs.n_samples,
        to: Optional[Path] = Opt.out_file(
            rf"""
            The path to a dataframe file for output.

            {CommonArgs.output_formats}

            [default: <input-path.parent>/<algorithm>-concordance.{MANDOS_SETTINGS.default_table_suffix}]
            """
        ),
        replace: bool = CommonArgs.replace,
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
            to = phi.parent / (psi.stem + "-" + algorithm + MANDOS_SETTINGS.default_table_suffix)
        if to.exists() and not replace:
            raise FileExistsError(f"File {to} already exists")
        phi = SimilarityDf.read_file(phi)
        psi = SimilarityDf.read_file(psi)
        concordance = TauConcordanceCalculator(samples, seed).calc(phi, psi)
        concordance.write_file(to)


__all__ = ["MiscCommands"]
