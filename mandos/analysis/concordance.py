"""
Calculations of concordance between annotations.
"""
import abc
import math
from typing import Sequence, Set, Collection, Tuple, Dict, Generator

import numpy as np
import pandas as pd
from typeddfs import TypedDfs

from mandos.analysis import AnalysisUtils, SimilarityDf

ConcordanceDf = (
    TypedDfs.typed("ConcordanceDf").require("sample", dtype=int).require("score", dtype=float)
).build()


class ConcordanceCalculator(metaclass=abc.ABCMeta):
    def __init__(self, n_samples: int, seed: int):
        self.n_samples = n_samples
        self.seed = seed
        self.rand = np.random.RandomState(seed)

    def calc(self, phi: SimilarityDf, psi: SimilarityDf) -> ConcordanceDf:
        if phi.columns.tolist() != psi.columns.tolist():
            raise ValueError(
                f"Mismatched compounds: {phi.columns.tolist()} != {psi.columns.tolist()}"
            )
        df = pd.DataFrame(data=self.generate(phi, psi), columns=["score"])
        df = df.reset_index()
        df.columns = ["sample", "score"]
        return ConcordanceDf(df)

    def generate(self, phi: SimilarityDf, psi: SimilarityDf) -> Generator[float, None, None]:
        for b in range(self.n_samples):
            phi_b = self.rand.choice(phi, replace=True)
            psi_b = self.rand.choice(psi, replace=True)
            yield self._calc(phi_b, psi_b)

    def _calc(self, phi: SimilarityDf, psi: SimilarityDf) -> float:
        raise NotImplemented()


class TauConcordanceCalculator(ConcordanceCalculator):
    def _calc(self, phi: SimilarityDf, psi: SimilarityDf) -> float:
        n = len(phi)
        numerator = self._n_z(phi, psi, 1) - self._n_z(phi, psi, -1)
        denominator = math.factorial(n) / (2 * math.factorial(n - 2))
        return numerator / denominator

    def _n_z(self, a: Sequence[float], b: Sequence[float], z: int) -> int:
        return int(
            np.sum(
                [
                    int(
                        np.sum(
                            [
                                int(np.sign(a[i] - a[j]) == z * np.sign(b[i] - b[j]) != 0)
                                for j in range(i)
                            ]
                        )
                    )
                    for i in range(len(a))
                ]
            )
        )


__all__ = ["ConcordanceCalculator", "TauConcordanceCalculator"]
