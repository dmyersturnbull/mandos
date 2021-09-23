"""
Plots.
"""
import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Tuple, Union, Mapping

import numpy as np
from pocketutils.core.exceptions import (
    BadCommandError,
    ImmutableError,
    MissingResourceError,
    XValueError,
)
from typeddfs import TypedDf, AffinityMatrixDf
from matplotlib.colors import Colormap

from mandos.analysis._plot_utils import MandosPlotStyling, plt, sns, Figure
from mandos.model.utils import CleverEnum
from mandos.analysis.io_defns import (
    PhiPsiSimilarityDfLongForm,
    PsiProjectedDf,
    EnrichmentDf,
    ConcordanceDf,
    SimilarityDfShortForm,
)


EN_DASH = "–"


@enum.unique
class RelPlotType(CleverEnum):
    scatter = 1
    line = 2
    regression = 3


@enum.unique
class CatPlotType(CleverEnum):
    bar = 1
    fold = 2
    box = 3
    violin = 4
    strip = 5
    swarm = 6


@dataclass(frozen=True, repr=True)
class PlotOptions:
    size: Optional[str]
    stylesheet: Optional[Path]
    rc: Mapping[str, Any]
    hue: Optional[str]
    palette: Union[None, Colormap, Mapping[str, str]]
    extra: Mapping[str, Any]

    @property
    def width_and_height(self) -> Tuple[float, float]:
        return MandosPlotStyling.fig_width_and_height(self.size)


@dataclass(frozen=True, repr=True)
class MandosPlotter:
    """"""

    rc: PlotOptions

    def __post_init__(self):
        if sns is None or plt is None:
            raise MissingResourceError(
                "Seaborn and matplotlib required for plotting. Install the 'plots' extra."
            )
        bad_kwargs = set(self.__dict__.keys()).intersection(self.rc.extra.keys())
        if len(bad_kwargs) > 0:
            raise XValueError(f"Overlapping args in extra: {bad_kwargs}")

    def _figure(self):
        width, height = self.rc.width_and_height
        fig = plt.gca()
        fig.set_figwidth(width)
        fig.set_figheight(height)
        return fig


@dataclass(frozen=True, repr=True)
class _CatPlotter(MandosPlotter):
    kind: CatPlotType
    group: bool
    ci: float
    boot: int
    seed: Optional[int]

    def get_kwargs(
        self, n_rows: int, n_categories: int, more: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        kwargs = dict(dropna=False)
        kwargs.update(**more)
        # the aspect probably doesn't matter much, but it definitely shouldn't be 1
        kwargs["aspect"] = n_categories
        if self.kind is CatPlotType.violin:
            kwargs.update(inner="quartile")
        if self.kind in [CatPlotType.bar, CatPlotType.box, CatPlotType.violin]:
            kwargs.update(saturation=1.0)
        if self.kind in [CatPlotType.swarm, CatPlotType.strip]:
            kwargs.update(edgecolor="black")
        if self.kind in [CatPlotType.bar, CatPlotType.fold]:
            kwargs.update(errcolor="black")
        if self.kind in [
            CatPlotType.bar,
            CatPlotType.fold,
            CatPlotType.swarm,
            CatPlotType.strip,
            CatPlotType.violin,
        ]:
            kwargs.update(dodge=self.group)
        if self.group and self.kind is CatPlotType.violin and n_categories == 2:
            kwargs.update(dodge=False, split=True)
        if self.rc.extra is not None:
            kwargs.update(**self.rc.extra)
        kwargs.update(seed=self.seed, ci=self.ci, n_boot=self.boot)
        return kwargs


@dataclass(frozen=True, repr=True)
class _RelPlotter(MandosPlotter):
    kind: RelPlotType
    ci: float
    boot: int
    seed: Optional[int]

    def get_kwargs(self, n_rows: int, n_cols: int, more: Mapping[str, Any]) -> Mapping[str, Any]:
        kwargs = dict(dropna=False, dashes=False)
        kwargs.update(**more)
        if self.rc.extra is not None:
            kwargs.update(**self.rc.extra)
        kwargs.update(seed=self.seed, ci=self.ci, n_boot=self.boot)
        return kwargs


@dataclass(frozen=True, repr=True)
class _HeatPlotter(MandosPlotter):
    vmin_percentile: float = 0
    vmax_percentile: float = 100

    def __post_init__(self):
        if self.rc.extra.get("mask") is not None:
            raise ImmutableError(f"Cannot set mask in {self.__class__.__name__}")

    def get_kwargs(self, data: AffinityMatrixDf, more: Mapping[str, Any]) -> Mapping[str, Any]:
        vmin = np.quantile(data.flatten(), self.vmin_percentile / 100)
        vmax = np.quantile(data.flatten(), self.vmax_percentile / 100)
        mask = data.values == np.nan
        kwargs = dict(
            vmin=vmin,
            vmax=vmax,
            square=True,
            mask=mask,
            hue=self.rc.hue,
            palette=self.rc.palette,
        )
        if self.rc.extra is not None:
            kwargs.update(**self.rc.extra)
        kwargs.update(**more)
        return kwargs


@dataclass(frozen=True, repr=True)
class ScorePlotter(_CatPlotter):
    """"""

    def plot(self, data: EnrichmentDf) -> Figure:
        data = data.copy()
        data: TypedDf = data
        data.only("score_name")  # make sure
        data[f"object{EN_DASH}predicate"] = data["object"] + " " + data["predicate"]
        data[f"predicate{EN_DASH}object"] = data["predicate"] + " " + data["object"]
        data = data.sort_natural(f"object{EN_DASH}predicate")
        with MandosPlotStyling.context(*self.rc.rc):
            if self.kind is CatPlotType.fold:
                self._plot_fold(data)
            else:
                self._plot_regular(data)
        return self._figure()

    def _plot_fold(self, data: EnrichmentDf):
        kwargs = dict(
            color="black",
            saturation=1,
            errcolor="black",
            dropna=False,
            ci=None,
            hue=self.rc.hue,
            palette=self.rc.palette,
        )
        if self.rc.extra is not None:
            kwargs.update({k: v for k, v in self.rc.extra if k != "saturation"})
        sns.catplot(
            kind="bar",
            x=f"predicate{EN_DASH}object",
            y="background",
            data=data,
            row="key",
            **kwargs,
        )
        kwargs = dict(
            color="black",
            saturation=0.3,
            errcolor="black",
            hue=self.rc.hue,
            palette=self.rc.palette,
        )
        if self.rc.extra is not None:
            kwargs.update(self.rc.extra)
        sns.catplot(
            kind="bar",
            data=data,
            x=f"predicate{EN_DASH}object",
            y="value",
            row="key",
            **kwargs,
        )

    def _plot_regular(self, data: EnrichmentDf):
        keys = data["keys"].unique()
        defaults = dict(
            saturation=1,
            errcolor="black",
            hue=self.rc.hue,
            palette=self.rc.palette,
        )
        kwargs = self.get_kwargs(len(keys), 1, defaults)
        sns.catplot(
            kind=self.kind.name,
            data=data,
            x=f"predicate{EN_DASH}object",
            y="value",
            row="key",
            **kwargs,
        )


@dataclass(frozen=True, repr=True)
class TauPlotter(_CatPlotter):
    """ """

    def plot(self, data: ConcordanceDf) -> Figure:
        phis = data["phi"].unique()
        # psis = data["psi"].unique()
        defaults = dict(
            saturation=1,
            errcolor="black",
            hue=self.rc.hue,
            palette=self.rc.palette,
        )
        kwargs = self.get_kwargs(len(phis), 1, defaults)
        with MandosPlotStyling.context(*self.rc.rc):
            sns.catplot(
                kind=self.kind.name,
                data=data,
                x="psi",
                y="tau",
                row="phi",
                **kwargs,
            )
        return self._figure()


@dataclass(frozen=True, repr=True)
class CorrPlotter(_RelPlotter):
    """"""

    def plot(self, data: PhiPsiSimilarityDfLongForm) -> Figure:
        phis = data["phi"].unique()
        psis = data["psi"].unique()
        with MandosPlotStyling.context(*self.rc.rc):
            if self.kind is RelPlotType.regression:
                defaults = dict(
                    truncate=True,
                    hue=self.rc.hue,
                    palette=self.rc.palette,
                )
                kwargs = self.get_kwargs(len(phis), len(psis), defaults)
                sns.lmplot(
                    data=data,
                    x="phi_value",
                    y="psi_value",
                    row="phi",
                    col="psi",
                    **kwargs,
                )
            else:
                kwargs = self.get_kwargs(len(phis), len(psis), {})
                sns.relplot(
                    kind=self.kind.name,
                    data=data,
                    x="phi_value",
                    y="psi_value",
                    row="phi",
                    col="psi",
                    **kwargs,
                )
        return self._figure()


@dataclass(frozen=True, repr=True)
class HeatmapPlotter(_HeatPlotter):
    def plot(self, data: SimilarityDfShortForm) -> Figure:
        data = data.triangle()
        kwargs = self.get_kwargs(data, {})
        with MandosPlotStyling.context(*self.rc.rc):
            sns.heatmap(
                data,
                **kwargs,
            )
        return self._figure()


@dataclass(frozen=True, repr=True)
class ProjectionPlotter(MandosPlotter):
    def plot(self, data: PsiProjectedDf) -> Figure:
        psis = set(data["psi"].unique())
        width, height = MandosPlotStyling.fig_width_and_height(self.rc.size)
        aspect = width / height
        col_wrap = int(np.ceil(np.sqrt(len(psis)) * aspect))
        kwargs = dict(
            col_wrap=col_wrap,
            hue=self.rc.hue,
            palette=self.rc.palette,
        )
        if self.rc.extra is not None:
            kwargs.update(**self.rc.extra)
        with MandosPlotStyling.context(*self.rc.rc):
            sns.relplot(
                kind="scatter",
                data=data,
                x="x",
                y="y",
                col="psi",
                **kwargs,
            )
        return self._figure()
