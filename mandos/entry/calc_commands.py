"""
Command-line interface for mandos.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

from pocketutils.core.exceptions import ResourceError

from mandos.entry._entry_utils import EntryUtils
from mandos.entry.searchers import InputFrame

from mandos.model.utils.setup import logger, MANDOS_SETUP
from mandos.analysis.io_defns import (
    SimilarityDfLongForm,
    PsiProjectedDf,
    SimilarityDfShortForm,
    EnrichmentDf,
    ConcordanceDf,
)
from mandos.analysis.concordance import ConcordanceCalculation
from mandos.analysis.distances import MatrixCalculation
from mandos.analysis.enrichment import EnrichmentCalculation, RealAlg, BoolAlg
from mandos.analysis.io_defns import ScoreDf
from mandos.analysis.prepping import MatrixPrep
from mandos.entry._common_args import CommonArgs
from mandos.entry._arg_utils import Arg, Opt, ArgUtils
from mandos.entry._common_args import CommonArgs as Ca
from mandos.model.hits import HitFrame
from mandos.model.settings import MANDOS_SETTINGS
from mandos.analysis.projection import UMAP


DEF_SUFFIX = MANDOS_SETTINGS.default_table_suffix

if UMAP is None:
    _umap_params = {}
else:
    _umap_params = {
        k: v
        for k, v in UMAP().get_params(deep=False).items()
        if k not in {"random_state", "metric"}
    }


class Aa:

    in_scores_table: Path = Opt.in_file(
        rf"""
        Path to a table containing scores.

        {Ca.input_formats}

        Required columns are 'inchikey', 'score_name', and 'score_value'.
        The InChI Keys must match those provided for the search.
        Each score must start with either 'score_' or 'is_'.

        {ArgUtils.df_description(ScoreDf)}
        """
    )

    out_enrichment: Optional[Path] = Opt.out_file(
        rf"""
        Path to write enrichment info.

        Use the format "<path>{os.sep}*<suffix>" to set the output format.
        (e.g. "output/*.csv.gz").
        If no suffix is provided, will interpret the path as a directory.

        {Ca.output_formats}

        One row will be included per predicate/object pair (or list of them), per bootstrap sample.
        Rows with a null bootstrap sample are not sub-sampled.
        Columns will correspond to the columns you provided.

        {ArgUtils.df_description(EnrichmentDf)}

        [default: <path>-correlation-<scores.filename>{MANDOS_SETTINGS.default_table_suffix}]
        """
    )

    in_matrix_long_form: Path = Arg.in_file(
        rf"""
        The path to a file with compound/compound similarity matrices.

        {Ca.input_formats}

        The matrix is "long-form" so that multiple matrices can be included.
        Columns are "inchikey_1", "inchikey_2", "key", and "type".
        The key is the specific similarity matrix; it is usually the search_key
        for psi matrices (computed from annotations from :search), and
        a user-provided value for phi matrices (typically of phenotypic similarity).
        The "type" column should contain either "phi" or "psi" accordingly.

        {ArgUtils.df_description(SimilarityDfLongForm)}
        """
    )

    out_matrix_long_form: Path = Opt.out_file(
        rf"""
        The path to a file with compound/compound similarity matrices.

        Use the format "<path>{os.sep}*<suffix>" to set the output format.
        (e.g. "output/*.csv.gz").
        If no suffix is provided, will interpret the path as a directory.

        {Ca.output_formats}

        The matrix is "long-form" so that multiple matrices can be included.
        You can provide just a filename suffix to change the format and suffix
        but otherwise use the default path.

        {ArgUtils.df_description(SimilarityDfLongForm)}

        [default: inferred from input path(s)]
        """,
    )

    in_matrix_short_form = Arg.in_file(
        rf"""
        The path to a file with a compound/compound similarity matrix.

        {Ca.input_formats}

        The matrix is "short-form": the first row and first column list the InChI Keys.
        The table must be symmetric (the rows and columns listed in the same order).

        {ArgUtils.df_description(SimilarityDfShortForm)}
        """
    )

    out_tau = Arg.out_file(
        rf"""
        Output file.

        Use the format "<path>{os.sep}*<suffix>" to set the output format.
        (e.g. "output/*.csv.gz").
        If no suffix is provided, will interpret the path as a directory.

        {Ca.output_formats}

        {ArgUtils.df_description(ConcordanceDf)}
        """
    )

    out_projection: Optional[Path] = Opt.out_file(
        rf"""
        Path to the output table.

        Use the format "<path>{os.sep}*<suffix>" to set the output format.
        (e.g. "output/*.csv.gz").
        If no suffix is provided, will interpret the path as a directory.

        {Ca.output_formats}

        {ArgUtils.df_description(PsiProjectedDf)}

        [default: <path>-<algorithm>{DEF_SUFFIX}],
        """
    )

    seed = Opt.val(r"Random seed (integer).", default=0)

    boot = Opt.val(
        r"""
        Generate results for <b> bootstrapped samples.

        Number of bootstrap samples (positive integer).
        If 0, will not perform a bootstrap.

        If set, will still include the non-bootstrapped results
        (sample=0 in the output).
        """,
        min=1,
        max=1000000,
        default=0,
    )


class CalcCommands:
    @staticmethod
    def calc_analysis(
        path: Path = Ca.in_annotations_file,
        phi: Path = Aa.in_matrix_long_form,
        scores: Path = Aa.in_scores_table,
        seed: int = Aa.seed,
        samples: int = Aa.boot,
        to: Optional[Path] = Ca.out_wildcard,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        """
        Shorthand for multiple calculations and plots.

        Generates n-triple statements and reified n-triples.
        Calculates correlation and enrichment using ``scores``,
        psi matrices (one per variable), and concordance between psi and tau matrices (tau).
        Plots UMAP of psi variables, enrichment bar plots, correlation violin plots,
        phi-vs-psi scatter and line plots, and phi-vs-psi (tau) violin plots.
        """
        MANDOS_SETUP(log, stderr)

    @staticmethod
    def calc_enrichment(
        path: Path = Ca.in_annotations_file,
        scores: Path = Aa.in_scores_table,
        bool_alg: Optional[str] = Opt.val(
            rf"""
            Algorithm to use for scores starting with 'is_'.

            Allowed values: {ArgUtils.list(BoolAlg)}
            """,
            default="alpha",
        ),
        real_alg: Optional[str] = Opt.val(
            rf"""
            Algorithm to use for scores starting with 'score_'.

            Allowed values: {ArgUtils.list(RealAlg)}
            """,
            default="weighted",
        ),
        on: bool = Opt.val(
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

            In general, this flag is useful for variables in which
            a *set of pairs* best is needed to describe a compound,
            and there are likely to be relatively few unique predicate/object pairs.
            """,
            default="choose",
        ),
        boot: int = Aa.boot,
        seed: int = Aa.seed,
        to: Optional[Path] = Aa.out_enrichment,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        """
        Compare annotations to user-supplied values.

        Calculates correlation between provided scores and object/predicate pairs.
        For booleans, compares annotations for hits and non-hits.
        See the docs for more info.
        """
        MANDOS_SETUP(log, stderr)
        default = f"{path}-{scores.name}-{on}{DEF_SUFFIX}"
        to = EntryUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path)
        scores = ScoreDf.read_file(scores)
        calculator = EnrichmentCalculation(bool_alg, real_alg, boot, seed)
        df = calculator.calculate(hits, scores)
        df.write_file(to, mkdirs=True)

    @staticmethod
    def calc_psi(
        path: Path = Arg.in_file(
            rf"""
            The path to a file from ``:calc:score``.

            {Ca.input_formats}
            """
        ),
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating similarity between annotation sets.

            Currently, only "j" (J') is supported. Refer to the docs for the equation.
            """,
            default="j",
        ),
        to: Path = Aa.out_matrix_long_form,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Calculate a similarity matrix from annotations.

        The data are output as a dataframe (CSV by default), where rows and columns correspond
        to compounds, and the cell i,j is the overlap J' in annotations between compounds i and j.
        """
        MANDOS_SETUP(log, stderr)
        default = path.parent / (algorithm + DEF_SUFFIX)
        to = EntryUtils.adjust_filename(to, default, replace)
        hits = HitFrame.read_file(path).to_hits()
        calculator = MatrixCalculation.create(algorithm)
        matrix = calculator.calc_all(hits)
        matrix.write_file(to)

    @staticmethod
    def calc_ecfp(
        path: Path = CommonArgs.in_compound_table,
        radius: int = Opt.val(r"""Radius of the ECFP fingerprint.""", default=4),
        n_bits: int = Opt.val(r"""Number of bits.""", default=2048),
        psi: bool = Opt.flag(
            r"""Use "psi" as the type in the resulting matrix instead of "phi"."""
        ),
        to: Path = Aa.out_matrix_long_form,
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
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
        MANDOS_SETUP(log, stderr)
        name = f"ecfp{radius}-n{n_bits}"
        default = path.parent / (name + DEF_SUFFIX)
        to = EntryUtils.adjust_filename(to, default, replace)
        df = InputFrame.read_file(path)
        kind = "psi" if psi else "phi"
        short = MatrixPrep.ecfp_matrix(df, radius, n_bits)
        long_form = MatrixPrep(kind, False, False, False).create({name: short})
        long_form.write_file(to)

    @staticmethod
    def calc_tau(
        phi: Path = Aa.in_matrix_long_form,
        psi: Path = Aa.in_matrix_long_form,
        algorithm: str = Opt.val(
            r"""
            The algorithm for calculating concordance.

            Currently, only "tau" is supported.
            This calculation is a modified Kendall’s  τ-a, where disconcordant ignores ties.
            See the docs for more info.
            """,
            default="tau",
        ),
        seed: int = Aa.seed,
        samples: int = Aa.boot,
        to: Optional[Path] = Opt.out_file(
            rf"""
            The path to a table for output.

            Use the format "<path>{os.sep}*<suffix>" to set the output format.
            (e.g. "output/*.csv.gz").
            If no suffix is provided, will interpret the path as a directory.

            {Ca.output_formats}

            [default: <input-path.parent>/<algorithm>-concordance.{DEF_SUFFIX}]
            """,
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
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
        MANDOS_SETUP(log, stderr)
        default = phi.parent / f"{psi.stem}-{algorithm}{DEF_SUFFIX}"
        to = EntryUtils.adjust_filename(to, default, replace)
        phi = SimilarityDfLongForm.read_file(phi)
        psi = SimilarityDfLongForm.read_file(psi)
        calculator = ConcordanceCalculation.create(algorithm, phi, psi, samples, seed)
        concordance = calculator.calc_all(phi, psi)
        concordance.write_file(to)

    @staticmethod
    def calc_projection(
        psi_matrix: Path = Aa.in_matrix_long_form,
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

            {ArgUtils.definition_list(_umap_params) if UMAP else "<list is unavailable>"}
            """,
            default="",
        ),
        to: Optional[Path] = Opt.val(
            rf"""
            Path to write a table of the projection coordinates.
            Will contain columns "x", "y", "inchikey", "key", and "data_source".

            Use the format "<path>{os.sep}*<suffix>" to set the output format.
            (e.g. "output/*.csv.gz").
            If no suffix is provided, will interpret the path as a directory.

            {Ca.output_formats}
            """
        ),
        replace: bool = Ca.replace,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Calculate compound UMAP from psi matrices.

        The input should probably be calculated from ``:calc:matrix``.
        Saves a table of the UMAP coordinates.
        """
        if algorithm == "umap" and UMAP is None:
            raise ResourceError(f"UMAP is not available")

    @staticmethod
    def calc_phi(
        matrices: List[Path] = Aa.in_matrix_short_form,
        kind: str = Opt.val(
            r"""
            Either "phi" or "psi".
            """,
            default="phi",
            hidden=True,
        ),
        to: Path = Aa.out_matrix_long_form,
        replace: bool = Ca.replace,
        normalize: bool = Opt.flag(
            r"""Rescale values to between 0 and 1 by (v-min) / (max-min). (Performed after negation.)"""
        ),
        log10: bool = Opt.val(r"""Rescales values by log10. (Performed after normalization.)"""),
        invert: bool = Opt.val(r"""Multiplies the values by -1. (Performed first.)"""),
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ):
        r"""
        Convert phi matrices to one long-form matrix.

        The keys will be derived from the filenames.
        """
        MANDOS_SETUP(log, stderr)
        default = "."
        if to is None:
            try:
                default = next(iter({mx.parent for mx in matrices}))
            except StopIteration:
                logger.warning(f"Outputting to {default}")
        to = EntryUtils.adjust_filename(to, default, replace)
        long_form = MatrixPrep(kind, normalize, log10, invert).from_files(matrices)
        long_form.write_file(to)


__all__ = ["CalcCommands"]
