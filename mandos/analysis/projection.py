import decorateme

from mandos.model.utils.setup import logger

try:
    from umap import UMAP
except ImportError:
    UMAP = None

from mandos.analysis.io_defns import PsiProjectedDf, SimilarityDfLongForm


@decorateme.auto_repr_str()
class UmapCalc:
    """
    Calculates UMAP.
    """

    def __init__(self, params):
        self.params = params

    def calc(self, df: SimilarityDfLongForm) -> PsiProjectedDf:
        """"""
        logger.info(f"Calculating UMAP on {len(df):,} items")


__all__ = ["UMAP", "UmapCalc"]
