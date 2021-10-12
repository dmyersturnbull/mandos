"""
Scoring (regression and enrichment) calculations.
"""
import abc
import enum
import math
from typing import (
    Any,
    Generic,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import numpy as np
import pandas as pd
from numpy.random import RandomState
from pocketutils.core.enums import CleverEnum

from mandos.analysis import AnalysisUtils as Au
from mandos.analysis.io_defns import EnrichmentDf, ScoreDf
from mandos.model.hit_dfs import HitDf
from mandos.model.hits import AbstractHit, KeyPredObj

S = TypeVar("S", bound=Union[int, float, bool])


class EnrichmentCalculator(Generic[S], metaclass=abc.ABCMeta):
    def calc(
        self, hits: Sequence[AbstractHit], scores: Mapping[str, S]
    ) -> Mapping[KeyPredObj, float]:
        pair_to_hits = Au.hit_multidict(hits, "to_key_pred_obj")
        results = {}
        for pair, the_hits in pair_to_hits.items():
            results[pair] = self.for_pair(hits, scores)
        return results

    def for_pair(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        raise NotImplementedError()

    @classmethod
    def alg_name(cls) -> str:
        raise NotImplementedError()


# noinspection PyAbstractClass
class _FoldCalculator(EnrichmentCalculator[bool]):
    """"""


# noinspection PyAbstractClass
class _RegressCalculator(EnrichmentCalculator[float]):
    """"""


class AlphaCalculator(_RegressCalculator):
    @classmethod
    def alg_name(cls) -> str:
        return "alpha"

    def for_pair(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        source_to_hits = Au.hit_multidict(hits, "data_source")
        vals = [
            self._calc_term(source_hits, scores) for source, source_hits in source_to_hits.items()
        ]
        return float(np.mean(vals))

    def _calc_term(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        vals = [
            Au.elle(hit.weight) * (2 * float(scores[hit.origin_inchikey] - 1)) ** 2 for hit in hits
        ]
        return float(np.mean(vals))


class SumWeightedCalc(_RegressCalculator):
    @classmethod
    def alg_name(cls) -> str:
        return "w-sum"

    def for_pair(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        return math.fsum([scores[hit.origin_inchikey] * hit.weight for hit in hits]) / len(hits)


class SumUnweightedCalc(_RegressCalculator):
    @classmethod
    def alg_name(cls) -> str:
        return "n-sum"

    def for_pair(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        return math.fsum([scores[hit.origin_inchikey] for hit in hits]) / len(hits)


class FoldWeightedCalc(_FoldCalculator):
    @classmethod
    def alg_name(cls) -> str:
        return "w-ratio"

    def for_pair(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        yes = [hit for hit in hits if scores[hit.origin_inchikey]]
        no = [hit for hit in hits if not scores[hit.origin_inchikey]]
        numerator = math.fsum((hit.weight for hit in yes))
        denominator = math.fsum((hit.weight for hit in no))
        if denominator == 0:
            return float("inf")
        return numerator / denominator


class FoldUnweightedCalc(_FoldCalculator):
    @classmethod
    def alg_name(cls) -> str:
        return "n-ratio"

    def for_pair(self, hits: Sequence[AbstractHit], scores: Mapping[str, S]) -> float:
        numerator = len([hit for hit in hits if scores[hit.origin_inchikey]])
        denominator = len([hit for hit in hits if not scores[hit.origin_inchikey]])
        if denominator == 0:
            return float("inf")
        return numerator / denominator


class _Alg(CleverEnum):
    """"""

    @classmethod
    def dtype(cls) -> Type[Any]:
        raise NotImplementedError()


class RealAlg(_Alg):
    alpha = enum.auto()
    weighted = enum.auto()
    unweighted = enum.auto()

    @classmethod
    def dtype(cls) -> Type[Any]:
        return float

    @property
    def clazz(self) -> Type[_RegressCalculator]:
        return {
            RealAlg.alpha: AlphaCalculator,
            RealAlg.weighted: SumWeightedCalc,
            RealAlg.unweighted: SumUnweightedCalc,
        }[self]


class BoolAlg(_Alg):
    weighted = enum.auto()
    unweighted = enum.auto()

    @classmethod
    def dtype(cls) -> Type[Any]:
        return bool

    @property
    def clazz(self) -> Type[_FoldCalculator]:
        return {
            BoolAlg.weighted: FoldWeightedCalc,
            BoolAlg.unweighted: FoldUnweightedCalc,
        }[self]


class EnrichmentCalculation:
    def __init__(
        self,
        bool_alg: str,
        real_alg: str,
        n_samples: int,
        seed: int,
    ):
        self.bool_alg = BoolAlg.of(bool_alg)
        self.real_alg = RealAlg.of(real_alg)
        self.n_samples = n_samples
        self.seed = seed
        self.state = RandomState(seed)

    def calculate(self, hit_df: HitDf, scores: Optional[ScoreDf]) -> EnrichmentDf:
        hits = hit_df.to_hits()
        if scores is None:
            scores = self._default_scores(hit_df)
        score_dict = self._get_dict(scores)
        results = self._calc(hits, score_dict, 0)
        for b in range(self.n_samples):
            b_hits = self.state.choice(hits, replace=True)
            results += self._calc(b_hits, score_dict, b)
        return EnrichmentDf.convert(results)

    def _calc(self, hits: Sequence[AbstractHit], score_dict, sample: int) -> Sequence[pd.DataFrame]:
        for score_name, (alg_type, score_vals) in score_dict.items():
            alg_instance = alg_type.clazz()
            forward = alg_instance.calc(hits, score_vals.to_dict())
            if alg_type.dtype == bool:
                reverse = alg_instance.calc(hits, (~score_vals).to_dict())
            else:
                reverse = alg_instance.calc(hits, (-score_vals).to_dict())
            return [self._make_df(forward, reverse, score_name, alg_type.name, sample)]

    def _default_scores(self, hit_df: HitDf) -> ScoreDf:
        inchikeys = hit_df["origin_inchikey"].unique().values
        counts = ScoreDf.of_constant(inchikeys, score_name="count")
        weights = ScoreDf.of_constant(inchikeys, score_name="count")
        return ScoreDf.concat([counts, weights])

    def _get_dict(self, scores: ScoreDf) -> Mapping[str, Tuple[_Alg, pd.Series]]:
        fold_cols = [c for c in scores.columns if c.startswith("is_") or c == "count"]
        score_cols = [c for c in scores.columns if c.startswith("score_") or c == "weight"]
        fold_dct = {c: (self.bool_alg, scores.set_index("inchikey")[c]) for c in fold_cols}
        score_dct = {c: (self.real_alg, scores.set_index("inchikey")[c]) for c in score_cols}
        return {**fold_dct, **score_dct}

    def _make_df(
        self,
        forward: Mapping[KeyPredObj, float],
        backward: Mapping[KeyPredObj, float],
        score: str,
        alg: str,
        sample: int,
    ):
        return pd.DataFrame(
            [
                pd.Series(
                    dict(
                        key=kpo.key,
                        predicate=kpo.pred,
                        object=kpo.obj,
                        score_name=score,
                        algorithm=alg,
                        sample=sample,
                        value=forward[kpo],
                        inverse=backward[kpo],
                    )
                )
                for kpo in forward.keys()
            ]
        )


__all__ = [
    "AlphaCalculator",
    "EnrichmentCalculator",
    "FoldUnweightedCalc",
    "FoldWeightedCalc",
    "SumUnweightedCalc",
    "SumWeightedCalc",
    "EnrichmentCalculation",
    "EnrichmentDf",
    "ScoreDf",
    "BoolAlg",
    "RealAlg",
]
