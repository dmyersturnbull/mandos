"""
Plots.
"""
from collections import Mapping
from dataclasses import dataclass

import seaborn as sns
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from mandos.analysis.concordance import ConcordanceDf


@dataclass(frozen=True, repr=True)
class HeatmapPlotter:
    vmin: float = 0
    vmax: float = 1

    def plot(self, ax: Axes) -> Axes:
        ax.pcolormesh()
        return ax


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
