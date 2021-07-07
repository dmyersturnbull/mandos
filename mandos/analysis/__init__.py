"""
Calculations.
"""
import math
from collections import defaultdict
from typing import Collection, Dict, Sequence, Set, Tuple, Union, Optional

from typeddfs import TypedDfs

from mandos.model.hits import AbstractHit, HitFrame, Pair

SimilarityDfShortForm = TypedDfs.typed("SimilarityDfShortForm").symmetric().build()

SimilarityDfLongForm = (
    TypedDfs.typed("SimilarityDfLongForm")
    .require("i", "j", dtype=str)
    .require("value", dtype=float)
    .reserve("phi", "psi", dtype=str)
).build()


SimilarityDf = Union[SimilarityDfLongForm, SimilarityDfShortForm]


def _to_long_form(
    self: SimilarityDfShortForm, phi: Optional[str] = None, psi: Optional[str] = None
) -> SimilarityDfLongForm:
    if (phi is None) == (psi is None):
        raise ValueError(f"Set either phi OR psi (phi={phi}, psi={psi}")
    stacked = self.stack(level=[self.column_names()]).reset_index()
    stacked.columns = ["i", "j", "value", *["phi" if phi else "psi"]]
    return SimilarityDfLongForm(stacked)


SimilarityDfShortForm.to_long_form = _to_long_form


class AnalysisUtils:
    @classmethod
    def elle(cls, x: float) -> float:
        return math.log10(1 + x)

    @classmethod
    def hit_multidict(cls, hits: Sequence[AbstractHit], key: str):
        x_to_hits = defaultdict(list)
        for hit in hits:
            x_to_hits[getattr(hit, key)].append(hit)
        return x_to_hits

    @classmethod
    def weights_of_pairs(
        cls, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]
    ) -> Dict[Pair, Tuple[float, float]]:
        """
        Calculates the sum of
        """
        union = {h.to_pair for h in hits1}.union({h.to_pair for h in hits2})
        return {p: (cls._score(hits1, p), cls._score(hits2, p)) for p in union}

    @classmethod
    def _score(cls, hits: Collection[AbstractHit], pair: Pair) -> int:
        return sum([h.weight for h in hits if h.to_pair == pair])


__all__ = ["AnalysisUtils", "SimilarityDfShortForm", "SimilarityDfLongForm", "SimilarityDf"]
