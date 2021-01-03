"""
TODO This module will probably be deleted.
"""

from __future__ import annotations
from collections import defaultdict
import logging
from typing import Sequence, Mapping, Set, TypeVar, Callable, SupportsFloat, Optional, Type, List
from typing import Tuple as Tup

import numpy as np
import pandas as pd
from typeddfs import TypedDfs, TypedDf

logger = logging.getLogger("mandos")
CompoundCompoundPair = Tup[str, str]


T = TypeVar("T")
Z = TypeVar("Z")


class ConfusionMatrix(TypedDf):
    @property
    def rows(self):
        """"""
        return [str(s) for s in self.index.tolist()]

    @property
    def cols(self):
        """"""
        return [str(s) for s in self.columns.tolist()]


class AffinityFunctions:
    """
    These are functions that can be passed into ``AffinityMatrix.from_function``.
    """

    @classmethod
    def jaccard(cls) -> Callable[[Set[Z], Set[Z]], float]:
        def x(a_set: Set[Z], b_set: Set[Z]):
            if len(a_set) == len(b_set) == 0:
                return float("NaN")
            return len(a_set.intersection(b_set)) / len(a_set.union(b_set))

        x.__name__ = "jaccard"
        return x

    @classmethod
    def bit_string_jaccard(cls) -> Callable[[str, str], float]:
        def x(a: str, b: str):
            if len(a) == len(b) == 0:
                return float("NaN")
            on_bits_a = {i for i, v in enumerate(a) if int(v) == 1}
            on_bits_b = {i for i, v in enumerate(b) if int(v) == 1}
            return len(on_bits_a.intersection(on_bits_b)) / len(on_bits_a.union(on_bits_b))

        x.__name__ = "bit_string_jaccard"
        return x

    @classmethod
    def identity(cls) -> Callable[[str, str], float]:
        def x(a: str, b: str):
            return float(a == b)

        x.__name__ = "identity"
        return x

    @classmethod
    def random_uniform(cls, state: np.random.RandomState) -> Callable[[Z, Z], float]:
        def x(a: Z, b: Z):
            return state.uniform(0, 1)

        x.__name__ = "random_uniform"
        return x

    @classmethod
    def rho_cm(cls, df: ConfusionMatrix) -> Callable[[str, str], float]:
        def x(d: ConfusionMatrix, a: str, b: str):
            ij = d.at[a, b]
            a_off_diag = np.sum(d.at[a, j] for j in d.cols if j != a)
            b_off_diag = np.sum(d.at[i, b] for i in d.rows if i != b)
            return ij / a_off_diag / b_off_diag

        def qq(a: str, b: str):
            return 0.5 * x(df, a, b) + 0.5 * x(ConfusionMatrix(df.transpose()), a, b)

        x.__name__ = "rho_cm"
        return qq

    @classmethod
    def pearson(
        cls, weights: Optional[Sequence[SupportsFloat]] = None
    ) -> Callable[[Sequence[SupportsFloat], Sequence[SupportsFloat]], float]:
        """
        Pearson correlation coefficient, possibly weighted.

        Args:
            weights:

        Returns:

        """
        weights = 1.0 if weights is None else np.array(weights, dtype=np.float64)

        def x(a: Sequence[SupportsFloat], b: Sequence[SupportsFloat]):
            a, b = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
            a = (a - a.mean()) / a.std()
            b = (b - b.mean()) / b.std()
            return np.average(a * b, weights=weights)

        x.__name__ = "pearson" if weights == 1.0 else "weighted-pearson"
        return x

    @classmethod
    def negative_minkowski(
        cls, order: float, weights: Optional[Sequence[SupportsFloat]] = None
    ) -> Callable[[Sequence[SupportsFloat], Sequence[SupportsFloat]], float]:
        """

        If ``order==0``, this is defined to return the number of elements that differ (number of nonzero).

        Args:
            order:
            weights:

        Returns:

        """
        weights = 1.0 if weights is None else np.array(weights, dtype=np.float64)

        def x(a: Sequence[SupportsFloat], b: Sequence[SupportsFloat]):
            a, b = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
            if np.isposinf(order):
                return -np.max(np.abs(a - b) * weights)
            elif order == 0:
                return -float(np.count_nonzero(a - b))
            else:
                return -np.float_power(
                    np.sum(np.float_power(np.abs(a - b) * weights, order)), 1 / order
                )

        x.__name__ = (
            "minkowski" + str(order) if weights == 1.0 else "weighted-minkowski" + str(order)
        )
        return x


class AffinityMatrix(TypedDf):
    """
    An affinity matrix of compound by compound.
    It has a single index, which is compound A,
    and the column labels are the compound B.
    """

    @classmethod
    def index_names(cls) -> List[str]:
        return ["name"]

    # @classmethod
    # def must_be_symmetric(cls) -> bool:
    #    return True

    @property
    def rows(self):
        """"""
        return [str(s) for s in self.index.tolist()]

    @property
    def cols(self):
        """"""
        return [str(s) for s in self.columns.tolist()]

    def restrict(self, to: Set[str]) -> AffinityMatrix:
        df = self[self["name"].isin(to)]
        df = df[[v for v in df.columns if v in to]]
        return AffinityMatrix.convert(df)

    def non_self_pairs(self) -> Mapping[CompoundCompoundPair, float]:
        """
        Gets the STRICT lower-triangular matrix, which excludes comparisons where the two labels are the same.
        The result is (n choose 2) matrix elements.

        Returns:
            A dict from comparison labels to their values in the matrix (i.e. (i, j)).
        """
        return {(a, b): value for (a, b), value in self.all_pairs().items() if a != b}

    def all_pairs(self) -> Mapping[CompoundCompoundPair, float]:
        """
        Gets the (non-strict) lower-triangular matrix.
        The result is (n(n+1)/2) matrix elements.

        Returns:
            A dict from comparison labels to their values in the matrix (i.e. (i, j)).
        """
        values = {}
        for i in range(0, len(self)):
            a = self.index.values[i]
            for j in range(0, i + 1):
                b = self.columns.values[j]
                # use (b, a) to get lower triangle
                values[(str(b).strip(), str(a).strip())] = self.iat[i, j]
        return values

    @classmethod
    def from_triples(cls, df: pd.DataFrame) -> AffinityMatrix:
        # TODO this function doesn't belong here
        dct = defaultdict(set)
        for row in df.itertuples():
            dct[row.compound_lookup].add(row.object_id + "," + row.predicate)
        return AffinityMatrix.from_function(dct, AffinityFunctions.jaccard())

    @classmethod
    def from_function(cls, items: Mapping[str, T], fn: Callable[[T, T], float]) -> AffinityMatrix:
        rows = []
        for a_label, a_value in items.items():
            rows.append(
                pd.Series(
                    {
                        "name": str(a_label),
                        **{
                            str(b_label): fn(a_value, b_value) for b_label, b_value in items.items()
                        },
                    }
                )
            )
        df = pd.DataFrame(rows)  # .astype(np.float64)
        df["name"] = df["name"].map(lambda v: str(v).replace(".0", "")).astype(str)
        df = df.set_index("name")
        afm = AffinityMatrix.convert(df)
        for c in afm.columns:
            afm[c] = afm[c].astype(np.float64)
        return afm


__all__ = [
    "AffinityMatrix",
    "AffinityFunctions",
]
