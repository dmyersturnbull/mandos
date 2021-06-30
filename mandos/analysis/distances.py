"""
Calculations of concordance between annotations.
"""
import abc
from collections import defaultdict
from typing import Sequence, Set, Collection, Tuple, Dict

import numpy as np
from typeddfs import TypedDfs

from mandos.analysis import AnalysisUtils, SimilarityDf
from mandos.model.hits import HitFrame, AbstractHit, Pair


def _elle(x: float) -> float:
    return np.log10(1 + x)


class MatrixCalculator(metaclass=abc.ABCMeta):
    def calc(self, hits: Sequence[AbstractHit]) -> SimilarityDf:
        raise NotImplemented()


class JPrimeMatrixCalculator(MatrixCalculator):
    def calc(self, hits: Sequence[AbstractHit]) -> SimilarityDf:
        inchikey_to_hits = defaultdict(list)
        for h in hits:
            inchikey_to_hits[h.origin_inchikey].append(h)
        data = defaultdict(dict)
        for (c1, hits1), (c2, hits2) in zip(inchikey_to_hits.items(), inchikey_to_hits.items()):
            data[c1][c2] = self._j_prime(hits1, hits2)
        return SimilarityDf.from_dict(data)

    def _j_prime(self, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]) -> float:
        sources = {h.data_source for h in hits1}.intersection({h.data_source for h in hits2})
        if len(sources) == 0:
            return np.nan
        return float(
            np.mean(
                [
                    self._jx(
                        [h for h in hits1 if h.data_source == source],
                        [h for h in hits1 if h.data_source == source],
                    )
                    for source in sources
                ]
            )
        )

    def _jx(self, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]) -> float:
        pair_to_weights = AnalysisUtils.weights_of_pairs(hits1, hits2)
        return float(
            np.mean(
                [self._wedge(ca, cb) / self._vee(ca, cb) for ca, cb in pair_to_weights.values()]
            )
        )

    def _wedge(self, ca: float, cb: float) -> float:
        return np.sqrt(_elle(ca) * _elle(cb))

    def _vee(self, ca: float, cb: float) -> float:
        return _elle(ca) + _elle(cb) - np.sqrt(_elle(ca) * _elle(cb))


__all__ = ["MatrixCalculator", "JPrimeMatrixCalculator"]
