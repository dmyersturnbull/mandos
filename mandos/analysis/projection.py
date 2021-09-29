from typing import Any, Mapping

try:
    from umap import UMAP
except ImportError:
    UMAP = None

from mandos.analysis.io_defns import PsiProjectedDf, SimilarityDfLongForm


class UmapCalc:
    """
    Calculates UMAP.
    """

    def __init__(self, params):
        self.params = params

    def calc(self, df: SimilarityDfLongForm) -> PsiProjectedDf:
        """"""


__all__ = ["UMAP", "UmapCalc"]
