from typing import Any, Mapping

try:
    from umap import UMAP
except ImportError:
    UMAP = None

from mandos.analysis.io_defns import SimilarityDfLongForm, PsiProjectedDf


class UmapCalc:
    """
    Calculates UMAP.
    """

    def calc(self, df: SimilarityDfLongForm) -> PsiProjectedDf:
        """"""


__all__ = ["UMAP", "UmapCalc"]
