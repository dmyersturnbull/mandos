"""
Calculations.
"""
import math
from collections import defaultdict
from typing import Collection, MutableMapping, Sequence, Tuple

import decorateme

from mandos.model.hits import AbstractHit, KeyPredObj


@decorateme.auto_utils()
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
    ) -> MutableMapping[KeyPredObj, Tuple[float, float]]:
        """
        Calculates the sum of
        """
        union = {h.to_key_pred_obj for h in hits1}.union({h.to_key_pred_obj for h in hits2})
        return {p: (cls._score(hits1, p), cls._score(hits2, p)) for p in union}

    @classmethod
    def _score(cls, hits: Collection[AbstractHit], pair: KeyPredObj) -> int:
        return sum([h.weight for h in hits if h.to_key_pred_obj == pair])


__all__ = ["AnalysisUtils"]
