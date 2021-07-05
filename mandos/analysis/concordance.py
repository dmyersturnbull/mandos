"""
Calculations of concordance between annotations.
"""
import abc
import enum
import math
from typing import Collection, Dict, Generator, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd
from typeddfs import TypedDfs

from mandos.analysis import AnalysisUtils, SimilarityDf
from mandos.model import CleverEnum

ConcordanceDf = (
    TypedDfs.typed("ConcordanceDf")
    .require("phi", "psi", dtype=str)
    .require("sample", dtype=int)
    .require("score", dtype=float)
).build()


class ConcordanceCalculator(metaclass=abc.ABCMeta):
    def __init__(self, n_samples: int, seed: int, phi_name: str, psi_name: str):
        self.n_samples = n_samples
        self.seed = seed
        self.rand = np.random.RandomState(seed)
        self.phi_name = phi_name
        self.psi_name = psi_name

    def calc(self, phi: SimilarityDf, psi: SimilarityDf) -> ConcordanceDf:
        if phi.columns.tolist() != psi.columns.tolist():
            raise ValueError(
                f"Mismatched compounds: {phi.columns.tolist()} != {psi.columns.tolist()}"
            )
        df = pd.DataFrame(data=self.generate(phi, psi), columns=["score"])
        df = df.reset_index()
        df["phi"] = self.phi_name
        df["psi"] = self.psi_name
        df.columns = ["sample", "score", "phi", "psi"]
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
        values = [self._i_sum(a, b, i, z) for i in range(len(a))]
        return int(np.sum(values))

    def _i_sum(self, a: np.array, b: np.array, i: int, z: int):
        values = [int(np.sign(a[i] - a[j]) == z * np.sign(b[i] - b[j]) != 0) for j in range(i)]
        return int(np.sum(values))


class ConcordanceAlg(CleverEnum):
    tau = enum.auto()


class ConcordanceCalculation:
    @classmethod
    def create(
        cls,
        algorithm: Union[str, ConcordanceAlg],
        phi_name: str,
        psi_name: str,
        n_samples: int,
        seed: int,
    ) -> ConcordanceCalculator:
        algorithm = ConcordanceAlg.of(algorithm)
        return TauConcordanceCalculator(
            n_samples=n_samples, seed=seed, phi_name=phi_name, psi_name=psi_name
        )


__all__ = [
    "ConcordanceCalculator",
    "TauConcordanceCalculator",
    "ConcordanceDf",
    "ConcordanceCalculation",
    "ConcordanceAlg",
]
