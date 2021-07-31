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
    from matplotlib.gridspec import GridSpec
    import umap
except ImportError:
    sns = None
    Axes = None
    Figure = None
    umap = None

from mandos.analysis.io_defns import SimilarityDfLongForm
from mandos.analysis.concordance import ConcordanceDf


@dataclass(frozen=True, repr=True)
class CorrPlotter:
    """"""

    def plot(self, phis: SimilarityDfLongForm, psis: SimilarityDfLongForm):
        gs = GridSpec(len(phis), len(psis))
        for phi in phis["key"]:
            for psi in psis["key"]:
                pass
        g.map_dataframe(sns.histplot, x="total_bill")


__all__ = ["CorrPlotter"]
