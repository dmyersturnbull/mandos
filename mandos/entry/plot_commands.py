"""
Command-line interface for mandos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Tuple, TypeVar

import decorateme
import pandas as pd
from pocketutils.core.chars import Chars
from pocketutils.core.exceptions import XValueError
from typeddfs import TypedDf
from typeddfs.cli_help import DfCliHelp

# noinspection PyProtectedMember
from mandos.analysis._plot_utils import (
    VIZ_RESOURCES,
    CompoundStyleDf,
    MandosPlotStyling,
    MandosPlotUtils,
    PhiPsiStyleDf,
    PredicateObjectStyleDf,
)
from mandos.analysis.io_defns import (
    EnrichmentDf,
    PhiPsiSimilarityDfLongForm,
    PsiProjectedDf,
    SimilarityDfLongForm,
)
from mandos.analysis.plots import (
    CatPlotType,
    CorrPlotter,
    PlotOptions,
    ProjectionPlotter,
    RelPlotType,
    ScorePlotter,
    TauPlotter,
)
from mandos.entry.calc_commands import Aa

# noinspection PyProtectedMember
from mandos.entry.utils._arg_utils import Arg, EntryUtils, Opt
from mandos.entry.utils._common_args import CommonArgs
from mandos.model.settings import SETTINGS
from mandos.model.utils import MANDOS_SETUP

DEF_SUFFIX = SETTINGS.table_suffix
nl = "\n\n"
IMG_SUFFIXES = {".pdf", ".png", ".svg", ".jpg", ".jpeg"}

T = TypeVar("T", bound=TypedDf)
V = TypeVar("V", bound=TypedDf)


@decorateme.auto_utils()
class Pa:

    in_style: str = Opt.val(
        rf"""
        The name of a matplotlib style or a path to a .mplstyle file.

        See https://matplotlib.org/stable/tutorials/introductory/customizing.html.
        [default: matplotlib default]
        """,
        show_default=False,
    )

    size: str = Opt.val(
        rf"""
        The width and height of a single figure.

        In the format "<width> x <height>' (e.g. "8.5 in x 11 in") or "<width>" (without height).
        If present, use simple expression with units or built-in, "registered" names.

        Example formats: "8.5 in", "8.5 in x 11 in", "2 cm + 5 in", "pnas.1-col x pnas.full-page".

        Registered widths: {", ".join(VIZ_RESOURCES.dims["heights"])}

        Registered heights: {", ".join(VIZ_RESOURCES.dims["widths"])}

        [default: matplotlib style default]
        """,
        show_default=False,
    )

    ci = Opt.val(
        f"""
        The upper side of the confidence interval, as a percentage.
        """,
        default=95.0,
    )

    out_fig_file: Optional[Path] = Opt.out_file(
        r"""
        Path to an output PDF or other figure file.

        PDF (.pdf) is recommended, but .svg, .png, and others are supported.

        [default: <input-dir>/<auto-generated-filename>.pdf]
        """
    )

    out_fig_dir: Optional[Path] = Opt.out_dir(
        r"""
        Path to an output directory for figures.

        [default: <input-dir>]
        """
    )

    in_projection: Optional[Path] = Opt.in_file(
        rf"""
        Path to data from ``:calc:project`` or a similar command.
        """
    )

    cat_plot_kind: str = (
        Opt.val(
            r"""
            The type of categorical-to-numerical plot.

            Can be: 'bar', 'fold', 'box', 'violin', 'strip', or 'swarm'.
            The type of plot: bar, box, violin, or swarm.
            'fold' plots an opaque bar plot for the score over a transparent one for the total.
            It is intended for integer scores representing simple counts.
            Bar (and box) plots include confidence/error bars.
            """,
            default="violin",
        ),
    )

    rel_plot_kind = Opt.val(
        rf"""
        The type of x{Chars.en}y relationship plot.

        Either 'scatter', 'line', 'regression:logistic', or 'regression:<order>.
        'regression:1' plots a linear regression line, 'regression:2' plots a quadratic,
        and so on. ('regression:linear', 'regression:quartic', etc., are also accepted.)
        Line and regression plots include confidence/error bands (see --ci and --boot).
        """,
        default="scatter",
    )

    group = Opt.flag(
        """
        Combine the colors (with --color) into plots.

        Applies only if --color is set and there is more than 1 category / color value.

        For strip and swarm plots, ignores the category, plotting all points together in
        single scatter plots. (Otherwise, slightly separates the colors along the x-axis.)
        For bar, box, and violin plots, places the bars immediately adjacent.
        For violin plots with exactly 2 colors, splits each violin into a half-violin per color.
        """
    )

    bandwidth = Opt.val(
        r"""
        Bandwidth as a float.

        Defaults to using Scott's algorithm.
        Only applies to violin plots.
        """
    )

    cut = Opt.val(
        r"""
        Distance, in units of bandwidth size, to extend the density past extreme points.

        Only applies to violin plots.
        """,
        default=2,
    )

    in_compound_viz: Optional[Path] = Opt.in_file(
        rf"""
        {DfCliHelp.help(CompoundStyleDf).get_short_text(nl=nl)}

        If set, ``--colors`` and ``--markers`` will refer to columns in this file.
        Otherwise, they will refer to columns in the input.
        """
    )

    in_pair_viz: Optional[Path] = Opt.in_file(
        rf"""
        {DfCliHelp.help(PredicateObjectStyleDf).get_short_text(nl=nl)}

        NOTE: This is currently not supported with pair intersection.

        If set, ``--colors`` and ``--markers`` will refer to columns in this file.
        Otherwise, they will refer to columns in the input.

        Any null (empty-string) value is taken to mean any/all.
        (The main use is to easily collapse over all predicates.)
        """
    )

    in_psi_viz: Optional[Path] = Opt.in_file(
        rf"""
        {DfCliHelp.help(CompoundStyleDf).get_short_text(nl=nl)}

        If set, ``--colors`` and ``--markers`` will refer to columns in this file.
        Otherwise, they will refer to columns in the input.
        """
    )

    colors: Optional[str] = Opt.val(
        rf"""
        A column that defines the 'group' and color.

        Each group is assigned a different color.
        If not specified, will use one color unless the plot requires more.

        See also: ``--palette``.
        """,
    )

    palette: Optional[str] = Opt.val(
        rf"""
        The name of a color palette.

        If not set, chooses a palette depending on the data type:

        - a vibrant palette for strings with a max of 26 unique items

        - a palette from white to black for numbers of the same sign (excluding NaN and 0)

        - a palette from blue to white to red for negative and positive numbers

        Choices: {", ".join(MandosPlotStyling.list_named_palettes())}.
        Some are only available for some data types.
        """
    )

    @classmethod
    def add_styling(cls, data: T, viz: Optional[TypedDf]) -> T:
        if viz is None:
            return data
        viz = pd.merge(data, viz, on=viz.get_typing().required_names)
        return CompoundStyleDf.convert(viz)

    @classmethod
    def read_rel_kind(cls, kind: str) -> Tuple[RelPlotType, Mapping[str, Any]]:
        type_ = RelPlotType.or_none(kind)
        if type_ is not None:
            return type_, {}
        type_, order = kind.split(":")
        if order == "logistic":
            return type_, dict(logistic=True)
        order = cls.get_degree(order)
        if order is None:
            raise XValueError(f"Unknown plot kind {kind}")
        return type_, dict(order=order)

    @classmethod
    def get_degree(cls, order: str) -> int:
        try:
            order = int(order)
        except ValueError:
            pass
        arities = dict(
            linear=1,
            quadratic=2,
            cubic=3,
            quartic=4,
            quintic=5,
            sextic=6,
            hexic=6,
            septic=7,
            heptic=7,
        )
        return arities[order]


class PlotCommands:
    @staticmethod
    def plot_enrichment(
        path: Path = Aa.in_scores_table,
        kind: str = Pa.cat_plot_kind,
        group: bool = Pa.group,
        ci: float = Pa.ci,
        boot: int = Aa.boot,
        seed: int = Aa.seed,
        bandwidth: float = Pa.bandwidth,
        cut: int = Pa.cut,
        viz: Optional[Path] = Pa.in_pair_viz,
        colors: Optional[str] = Pa.colors,
        palette: Optional[str] = Pa.palette,
        size: Optional[str] = Pa.size,
        style: Optional[str] = Pa.in_style,
        to: Optional[Path] = Pa.out_fig_dir,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Plot correlation to scores.

        Visualizes the correlation between predicate/object pairs and user-supplied scores.
        Will output one figure (file) per scoring function.
        Will plot over a grid, one row per key/source pair and column per predicate/object pair.
        """
        MANDOS_SETUP(log, stderr)
        kind = CatPlotType.of(kind)
        to, suffix = EntryUtils.adjust_dir_name(to, path.parent, suffixes=IMG_SUFFIXES)
        df = EnrichmentDf.read_file(path)
        viz = None if viz is None else PredicateObjectStyleDf.read_file(viz)
        df = Pa.add_styling(df, viz)
        palette = MandosPlotStyling.choose_palette(df, colors, palette)
        extra = dict(bandwith=bandwidth, cut=cut) if kind is CatPlotType.violin else {}
        rc = PlotOptions(
            size=size,
            style=style,
            rc={},
            hue=colors,
            palette=palette,
            extra=extra,
        )
        plotter = ScorePlotter(
            rc=rc,
            kind=kind,
            group=group,
            ci=ci,
            seed=seed,
            boot=boot,
        )
        for score_name in df["score_name"].unique():
            fig = plotter.plot(df)
            MandosPlotUtils.save(fig, to / f"{score_name}-{kind}-plot{suffix}")

    @staticmethod
    def plot_phi_psi(
        path: Path = Aa.in_matrix_long_form,
        kind: str = Pa.rel_plot_kind,
        ci: float = Pa.ci,
        boot: int = Aa.boot,
        seed: int = Aa.seed,
        viz: Optional[Path] = Pa.in_psi_viz,
        colors: Optional[str] = Pa.colors,
        palette: Optional[str] = Pa.palette,
        size: Optional[str] = Pa.size,
        style: Optional[str] = Pa.in_style,
        to: Optional[Path] = Pa.out_fig_file,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Plot line plots of phi against psi.

        Plots scatter plots of (phi, psi) values, sorted by phi values.
        All plots are log/log (all similarity values should be scaled from 0 to 1).

        For each unique phi matrix and psi matrix, flattens the matrices and plots
        the flattened (n choose 2 - n) pairs of each jointly, phi mapped to the y-axis
        and psi mapped to the x-axis.

        Will show values for all psi variables together.
        If --colors is not set, will choose a palette.
        """
        MANDOS_SETUP(log, stderr)
        default = path.parent / f"{path.name}-{kind}-plot.pdf"
        to = EntryUtils.adjust_filename(to, default, True, suffixes=IMG_SUFFIXES)
        df = PhiPsiSimilarityDfLongForm.read_file(path)
        viz = None if viz is None else PhiPsiStyleDf.read_file(viz)
        df = Pa.add_styling(df, viz)
        palette = MandosPlotStyling.choose_palette(df, colors, palette)
        kind, extra = Pa.read_rel_kind(kind)
        rc = PlotOptions(
            size=size,
            style=style,
            rc={},
            hue=colors,
            palette=palette,
            extra=extra,
        )
        plotter = CorrPlotter(
            rc=rc,
            kind=kind,
            ci=ci,
            boot=boot,
            seed=seed,
        )
        fig = plotter.plot(df)
        MandosPlotUtils.save(fig, to)

    @staticmethod
    def plot_tau(
        path: Path = Arg.in_file(
            rf"""
            Output file from ``:calc:tau``.
            """
        ),
        kind: str = Pa.cat_plot_kind,
        group: bool = Pa.group,
        ci: float = Pa.ci,
        boot: int = Aa.boot,
        seed: int = Aa.seed,
        bandwidth: float = Pa.bandwidth,
        cut: int = Pa.cut,
        viz: Optional[Path] = Pa.in_psi_viz,
        colors: Optional[str] = Pa.colors,
        palette: Optional[str] = Pa.palette,
        size: Optional[str] = Pa.size,
        style: Optional[str] = Pa.in_style,
        to: Optional[Path] = Pa.out_fig_file,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Plot violin plots or similar from tau values.

        The input data should be generated by ``:calc:phi-vs-psi.tau``.

        Will plot each (phi, psi) pair over a grid, one row per phi and one column per psi.
        """
        MANDOS_SETUP(log, stderr)
        kind = CatPlotType.of(kind)
        default = path.parent / (f"{path.name}-{kind}-plot.pdf")
        to = EntryUtils.adjust_filename(to, default, suffixes=IMG_SUFFIXES)
        df: SimilarityDfLongForm = SimilarityDfLongForm.read_file(path)
        viz = None if viz is None else PhiPsiStyleDf.read_file(viz)
        df = Pa.add_styling(df, viz)
        palette = MandosPlotStyling.choose_palette(df, colors, palette)
        extra = dict(bandwith=bandwidth, cut=cut) if kind is CatPlotType.violin else {}
        rc = PlotOptions(
            size=size,
            style=style,
            rc={},
            hue=colors,
            palette=palette,
            extra=extra,
        )
        plotter = TauPlotter(
            rc=rc,
            kind=kind,
            group=group,
            ci=ci,
            boot=boot,
            seed=seed,
        )
        fig = plotter.plot(df)
        MandosPlotUtils.save(fig, to)

    @staticmethod
    def plot_heatmap(
        path: Path = Aa.in_matrix_long_form,
        size: Optional[str] = Pa.size,
        style: Optional[str] = Pa.in_style,
        to: Optional[Path] = Pa.out_fig_file,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Plot a heatmap of correlation between compounds.

        Will output one figure / file per correlation definition ('key' column).
        """
        MANDOS_SETUP(log, stderr)
        default = path.parent / (path.name + "-heatmap-plot.pdf")
        to = EntryUtils.adjust_filename(to, default, True, suffixes=IMG_SUFFIXES)
        df = PsiProjectedDf.read_file(path)
        rc = PlotOptions(
            size=size,
            style=style,
            rc={},
            hue=None,
            palette=None,
            extra={},
        )
        fig = ProjectionPlotter(rc).plot(df)
        MandosPlotUtils.save(fig, to)

    @staticmethod
    def plot_projection(
        path: Path = Pa.in_projection,
        viz: Optional[Path] = Pa.in_compound_viz,
        colors: Optional[str] = Pa.colors,
        palette: Optional[str] = Pa.palette,
        size: Optional[str] = Pa.size,
        style: Optional[str] = Pa.in_style,
        to: Optional[Path] = Pa.out_fig_file,
        log: Optional[Path] = CommonArgs.log,
        stderr: bool = CommonArgs.stderr,
    ) -> None:
        r"""
        Plot UMAP, etc. of compounds from psi matrices.

        Will plot the psi variables over a grid.
        """
        MANDOS_SETUP(log, stderr)
        default = path.parent / (path.name + "-plot.pdf")
        to = EntryUtils.adjust_filename(to, default, True, suffixes=IMG_SUFFIXES)
        df = PsiProjectedDf.read_file(path)
        viz = None if viz is None else CompoundStyleDf.read_file(viz)
        df = Pa.add_styling(df, viz)
        palette = MandosPlotStyling.choose_palette(df, colors, palette)
        rc = PlotOptions(
            size=size,
            style=style,
            rc={},
            hue=colors,
            palette=palette,
            extra={},
        )
        fig = ProjectionPlotter(rc).plot(df)
        MandosPlotUtils.save(fig, to)


__all__ = ["PlotCommands"]
