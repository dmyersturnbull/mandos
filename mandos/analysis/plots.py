"""
Plots.
"""
from collections import Mapping
from dataclasses import dataclass
from typing import Any

try:
    import seaborn as sns
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    import umap
except ImportError:
    sns = None
    Axes = None
    Figure = None
    umap = None

from mandos.analysis import SimilarityDfLongForm
from mandos.analysis.concordance import ConcordanceDf


@dataclass(frozen=True, repr=True)
class HeatmapPlotter:
    vmin: float = 0
    vmax: float = 1

    def plot(self, ax: Axes) -> Axes:
        ax.pcolormesh()
        return ax


@dataclass(frozen=True, repr=True)
class UmapPlotter:
    params: Mapping[str, Any]

    def plot(self, ax: Axes) -> Axes:
        pass


@dataclass(frozen=True, repr=True)
class CorrPlotter:
    """"""

    def plot(self, phis: SimilarityDfLongForm, psis: SimilarityDfLongForm):
        pass


@dataclass(frozen=True, repr=True)
class ViolinPlotter:
    def plot(self, concordance: ConcordanceDf) -> Axes:
        palette = sns.color_palette(["#0000c0", "#888888"])
        return sns.violinplot(
            data=concordance,
            x="psi",
            y="score",
            hue="phi",
            split=True,
            scale_hue=False,
            palette=palette,
        )
