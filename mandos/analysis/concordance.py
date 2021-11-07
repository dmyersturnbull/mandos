"""
Calculations of concordance between annotations.
"""
import abc
import enum
import math
from typing import Generator, Sequence, Type, Union

import decorateme
import numpy as np
import pandas as pd
from pocketutils.core.enums import CleverEnum
from pocketutils.core.exceptions import MismatchedDataError

from mandos.analysis.io_defns import (
    ConcordanceDf,
    SimilarityDfLongForm,
    SimilarityDfShortForm,
)
from mandos.model.utils.setup import logger


@decorateme.auto_repr_str()
class ConcordanceCalculator(metaclass=abc.ABCMeta):
    def __init__(self, n_samples: int, seed: int):
        self.n_samples = n_samples
        self.seed = seed
        self.rand = np.random.RandomState(seed)

    def calc_all(self, phis: SimilarityDfLongForm, psis: SimilarityDfLongForm) -> ConcordanceDf:
        for phi in phis["phi"].unique():
            for psi in psis["psi"].unique():
                phi_mx = phis[phis["phi"] == phi]
                psi_mx = phis[phis["psi"] == psi]
                self.calc(phi_mx, psi_mx, phi, psi)

    def calc(
        self, phi: SimilarityDfShortForm, psi: SimilarityDfShortForm, phi_name: str, psi_name: str
    ) -> ConcordanceDf:
        logger.info(f"Calculating {phi_name} / {psi_name}")
        phi_cols, psi_cols = phi.columns.tolist(), psi.columns.tolist()
        if phi_cols != psi_cols:
            raise MismatchedDataError(f"Mismatched compounds: {phi_cols} != {psi_cols}")
        df = pd.DataFrame(data=self.generate(phi, psi), columns=["score"])
        df = df.reset_index()
        df["phi"] = phi_name
        df["psi"] = psi_name
        df.columns = ["sample", "tau", "phi", "psi"]
        return ConcordanceDf.convert(df)

    def generate(
        self, phi: SimilarityDfShortForm, psi: SimilarityDfShortForm
    ) -> Generator[float, None, None]:
        if self.n_samples == 1:
            yield self._calc(phi, psi)
        else:
            for b in range(self.n_samples):
                phi_b = self.rand.choice(phi, replace=True)
                psi_b = self.rand.choice(psi, replace=True)
                yield self._calc(phi_b, psi_b)

    def _calc(self, phi: SimilarityDfShortForm, psi: SimilarityDfShortForm) -> float:
        raise NotImplemented()


class TauConcordanceCalculator(ConcordanceCalculator):
    def _calc(self, phi: SimilarityDfShortForm, psi: SimilarityDfShortForm) -> float:
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

    @property
    def clazz(self) -> Type[ConcordanceCalculator]:
        return {ConcordanceAlg.tau: TauConcordanceCalculator}[self]


@decorateme.auto_utils()
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
        algorithm = ConcordanceAlg.of(algorithm).clazz
        return algorithm(n_samples=n_samples, seed=seed, phi_name=phi_name, psi_name=psi_name)


__all__ = [
    "ConcordanceAlg",
    "ConcordanceCalculation",
    "ConcordanceCalculator",
    "ConcordanceDf",
    "TauConcordanceCalculator",
]
