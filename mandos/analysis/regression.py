"""
Scoring (regression and enrichment) calculations.
"""
import abc
import enum
import math
from typing import Generic, Mapping, Sequence, Type, TypeVar, Union

import pandas as pd
from typeddfs import TypedDfs

from mandos.analysis import AnalysisUtils as Au
from mandos.model import CleverEnum
from mandos.model.hits import AbstractHit, HitFrame, Pair

S = TypeVar("S", bound=Union[int, float, bool])


EnrichmentDf = (
    TypedDfs.typed("EnrichmentDf")
    .require("predicate", "object", dtype=str)
    .require("samples", dtype=int)
).build()
# extra cols are, e.g., alpha(score_1), alpha(is_hit)


ScoreDf = (
    TypedDfs.typed("ScoreDf")
    .require("inchikey", dtype=str, index=True)
    .reserve("score")
    .reserve("is_hit", dtype=bool)
).build()
# extra cols are, e.g., score_1, score_hello, is_lethal, is_good


def _score_cols(self: ScoreDf) -> Sequence[str]:
    return [
        col
        for col in self.columns
        if col == "score" or col.startswith("score_") or col.startswith("is_")
    ]


def _all_scores(self: ScoreDf) -> Mapping[str, Mapping[str, S]]:
    results = {}
    for c in self.score_cols:
        results[c] = self[c].to_dict()
    return results


ScoreDf.score_cols = _score_cols
ScoreDf.all_scores = _all_scores


class EnrichmentCalculator(Generic[S], metaclass=abc.ABCMeta):
    def __init__(self, scores: Mapping[str, S]):
        self.scores = scores

    def calc(self, hits: Sequence[AbstractHit]) -> Mapping[Pair, float]:
        pair_to_hits = Au.hit_multidict(hits, "to_pair")
        results = {}
        for pair, the_hits in pair_to_hits.items():
            results[pair] = self.for_pair(hits)
        return results

    def for_pair(self, hits: Sequence[AbstractHit]) -> float:
        raise NotImplementedError()


class AlphaCalculator(EnrichmentCalculator[S]):
    def for_pair(self, hits: Sequence[AbstractHit]) -> float:
        source_to_hits = Au.hit_multidict(hits, "data_source")
        terms = []
        for source, source_hits in source_to_hits.items():
            terms.append(self._calc_term(source_hits))
        return math.fsum(terms) / len(terms)

    def _calc_term(self, hits: Sequence[AbstractHit]) -> float:
        values = [
            Au.elle(hit.value) * (2 * float(self.scores[hit.origin_inchikey] - 1)) ** 2
            for hit in hits
        ]
        return math.fsum(values) / len(values)


class FoldUnweightedCalc(EnrichmentCalculator[bool]):
    def for_pair(self, hits: Sequence[AbstractHit]) -> float:
        numerator = len([hit for hit in hits if self.scores[hit.origin_inchikey]])
        denominator = len([hit for hit in hits if not self.scores[hit.origin_inchikey]])
        if denominator == 0:
            return float("inf")
        return numerator / denominator


class FoldWeightedCalc(EnrichmentCalculator[bool]):
    def for_pair(self, hits: Sequence[AbstractHit]) -> float:
        yes = [hit for hit in hits if self.scores[hit.origin_inchikey]]
        no = [hit for hit in hits if not self.scores[hit.origin_inchikey]]
        numerator = math.fsum((hit.value for hit in yes))
        denominator = math.fsum((hit.value for hit in no))
        if denominator == 0:
            return float("inf")
        return numerator / denominator


class SumWeightedCalc(EnrichmentCalculator[S]):
    def for_pair(self, hits: Sequence[AbstractHit]) -> float:
        return math.fsum([self.scores[hit.origin_inchikey] * hit.value for hit in hits]) / len(hits)


class SumUnweightedCalc(EnrichmentCalculator[S]):
    def for_pair(self, hits: Sequence[AbstractHit]) -> float:
        return math.fsum([self.scores[hit.origin_inchikey] for hit in hits]) / len(hits)


class EnrichmentAlg(CleverEnum):
    """ """

    alpha = enum.auto()
    fold = enum.auto()
    fold_w = enum.auto()
    sum = enum.auto()
    sum_w = enum.auto()

    @property
    def description(self) -> str:
        s = self.symbol
        return {
            EnrichmentAlg.alpha: rf"[float] {s}(p) = Mean product of rescaled weights and scores; see the docs",
            EnrichmentAlg.fold: rf"[bool] {s}(p) = #(c has p and hit) / #(c has p and not hit)",
            EnrichmentAlg.fold_w: rf"[bool] {s}(p) = ∑(w(c, pair) s.t. c is hit) / ∑(w(c, pair) s.t. c not hit)",
            EnrichmentAlg.sum: rf"{s}(p) = ∑(score(c) s.t. c has p)",
            EnrichmentAlg.sum_w: rf"{s}(p) = ∑(score(c) × w(c, p) for all c)",
        }[self]

    @property
    def symbol(self) -> str:
        return {
            EnrichmentAlg.alpha: "α",
            EnrichmentAlg.fold: r"β",
            EnrichmentAlg.fold_w: "β*",
            EnrichmentAlg.sum: r"γ",
            EnrichmentAlg.sum_w: r"γ*",
        }[self]

    @property
    def clazz(self) -> Type[EnrichmentCalculator]:
        return {
            EnrichmentAlg.alpha: AlphaCalculator,
            EnrichmentAlg.fold: FoldUnweightedCalc,
            EnrichmentAlg.fold_w: FoldWeightedCalc,
            EnrichmentAlg.sum: SumUnweightedCalc,
            EnrichmentAlg.sum_w: SumWeightedCalc,
        }[self.name]


class EnrichmentCalculation:
    def calc(
        self, data: HitFrame, score_df: ScoreDf, algorithm: Union[str, EnrichmentAlg]
    ) -> EnrichmentDf:
        hits = ...
        alg_clazz = EnrichmentDf.of(algorithm).clazz
        alg_name = str(algorithm)
        samples_per_pair = {k: len(v) for k, v in Au.hit_multidict(hits, "pair").items()}
        results = {}
        for col, scores in score_df.all_scores():
            calculated = alg_clazz(scores).calc(hits)
            results[col] = calculated
        return EnrichmentDf(
            [
                pd.Series(
                    {
                        **dict(
                            predicate=pair.pred,
                            object=pair.obj,
                            samples=n_samples,
                        ),
                        **{f"{alg_name}({c})": vs[pair] for c, vs in results.items()},
                    }
                )
                for pair, n_samples in samples_per_pair.items()
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
    "EnrichmentAlg",
    "EnrichmentDf",
    "ScoreDf",
]
