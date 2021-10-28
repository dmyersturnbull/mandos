"""
Calculations of concordance between annotations.
"""
import abc
import enum
import math
import time
from collections import defaultdict
from typing import Collection, Sequence, Type, Union

import decorateme
import numpy as np
import pandas as pd
from pocketutils.core.chars import Chars
from pocketutils.core.enums import CleverEnum
from pocketutils.tools.unit_tools import UnitTools

from mandos.analysis import AnalysisUtils as Au
from mandos.analysis.io_defns import SimilarityDfLongForm, SimilarityDfShortForm
from mandos.model.hits import AbstractHit

# note that most of these math functions are much faster than their numpy counterparts
# if we're not broadcasting, it's almost always better to use them
# some are more accurate, too
# e.g. we're using fsum rather than sum
from mandos.model.utils.setup import logger


@decorateme.auto_repr_str()
class MatrixCalculator(metaclass=abc.ABCMeta):
    def calc_all(self, hits: Sequence[AbstractHit]) -> SimilarityDfLongForm:
        raise NotImplemented()


class _Inf:
    def __init__(self, n: int):
        self.n = n
        self.used, self.t0, self.nonzeros = set(), time.monotonic(), 0

    def is_used(self, c1: str, c2: str) -> bool:
        return (c1, c2) in self.used or (c2, c1) in self.used

    def got(self, c1: str, c2: str, z: float) -> None:
        self.used.add((c1, c2))
        self.nonzeros += int(c1 != c2 and not np.isnan(z) and 0 < z < 1)
        i = self.i
        if i % 5000 == 0:
            lg_ = next(
                t_
                for s_, t_ in zip([50000, 10000, 1000], ["success", "info", "debug"])
                if not i % s_
            )
            self.log(lg_)

    @property
    def i(self) -> int:
        return len(self.used)

    def log(self, level: str) -> None:
        delta = UnitTools.delta_time_to_str(time.monotonic() - self.t0, space=Chars.narrownbsp)
        logger.log(
            level.upper(),
            f"Processed {self.i:,}/{self.n:,} pairs in {delta};"
            + f" {self.nonzeros:,} ({self.nonzeros / self.i * 100:.1f}%) are nonzero",
        )


class JPrimeMatrixCalculator(MatrixCalculator):
    def calc_all(self, hits: Sequence[AbstractHit]) -> SimilarityDfLongForm:
        key_to_hit = Au.hit_multidict(hits, "search_key")
        logger.notice(f"Calculating J on {len(key_to_hit)} keys from {len(hits)} hits")
        dfs = []
        for key, key_hits in key_to_hit.items():
            df: SimilarityDfShortForm = self.calc_one(key, key_hits)
            df = df.to_long_form(kind="psi", key=key)
            dfs += [df]
        return SimilarityDfLongForm(pd.concat(dfs))

    def calc_one(self, key: str, hits: Sequence[AbstractHit]) -> SimilarityDfShortForm:
        ik2hits = Au.hit_multidict(hits, "origin_inchikey")
        logger.info(f"Calculating J on {key} for {len(ik2hits)} compounds and {len(hits)} hits")
        data = defaultdict(dict)
        inf = _Inf(n=int(len(ik2hits) * (len(ik2hits) - 1) / 2))
        for (c1, hits1) in ik2hits.items():
            for (c2, hits2) in ik2hits.items():
                if inf.is_used(c1, c2):
                    continue
                z = 1 if c1 == c2 else self._j_prime(hits1, hits2)
                data[c1][c2] = z
                inf.got(c1, c2, z)
        inf.log("notice")
        return SimilarityDfShortForm.from_dict(data)

    def _j_prime(self, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]) -> float:
        if len(hits1) == 0 or len(hits2) == 0:
            return 0
        sources = {h.data_source for h in hits1}.intersection({h.data_source for h in hits2})
        if len(sources) == 0:
            return np.nan
        values = [
            self._jx(
                [h for h in hits1 if h.data_source == source],
                [h for h in hits2 if h.data_source == source],
            )
            for source in sources
        ]
        return float(math.fsum(values) / len(values))

    def _jx(self, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]) -> float:
        pair_to_weights = Au.weights_of_pairs(hits1, hits2)
        values = [self._wedge(ca, cb) / self._vee(ca, cb) for ca, cb in pair_to_weights.values()]
        return float(math.fsum(values) / len(values))

    def _wedge(self, ca: float, cb: float) -> float:
        return math.sqrt(Au.elle(ca) * Au.elle(cb))

    def _vee(self, ca: float, cb: float) -> float:
        return Au.elle(ca) + Au.elle(cb) - math.sqrt(Au.elle(ca) * Au.elle(cb))


class MatrixAlg(CleverEnum):
    j = enum.auto()

    @property
    def clazz(self) -> Type[MatrixCalculator]:
        return {MatrixAlg.j: JPrimeMatrixCalculator}[self]


@decorateme.auto_utils()
class MatrixCalculation:
    @classmethod
    def create(cls, algorithm: Union[str, MatrixAlg]) -> MatrixCalculator:
        return MatrixAlg.of(algorithm).clazz()


__all__ = ["MatrixCalculator", "JPrimeMatrixCalculator", "MatrixCalculation", "MatrixAlg"]
