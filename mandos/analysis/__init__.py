"""
Calculations.
"""
from collections import defaultdict
from typing import Sequence, Set, Collection, Tuple, Dict

import numpy as np
from typeddfs import TypedDfs

from mandos.model.hits import HitFrame, AbstractHit, Pair


SimilarityDf = TypedDfs.typed("DistanceDf").symmetric().build()


class AnalysisUtils:
    @classmethod
    def weights_of_pairs(
        cls, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]
    ) -> Dict[Pair, Tuple[float, float]]:
        """
        Calculates the sum of
        """
        union = {h.to_pair() for h in hits1}.union({h.to_pair() for h in hits2})
        return {p: (cls._score(hits1, p), cls._score(hits2, p)) for p in union}

    @classmethod
    def _score(cls, hits: Collection[AbstractHit], pair: Pair) -> int:
        return sum([h.value for h in hits if h.to_pair() == pair])


__all__ = ["AnalysisUtils", "SimilarityDf"]
