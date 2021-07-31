"""
Definitions of input types for analysis.
"""

import math
from collections import defaultdict
from itertools import cycle
from typing import Collection, Dict, Sequence, Set, Tuple, Union, Optional

import numpy as np
import pandas as pd
from typeddfs import TypedDfs


def _is_symmetric(df: pd.DataFrame):
    if not np.array_equal(df.values, df.T.values):
        return f"The matrix is not symmetric"


SimilarityDfShortForm = (
    TypedDfs.typed("SimilarityDfShortForm")
    .symmetric()
    .condition(_is_symmetric)
    .add_read_kwargs("csv", index_col=0)  # TODO: shouldn't be needed
).build()

SimilarityDfLongForm = (
    TypedDfs.typed("SimilarityDfLongForm")
    .require("inchikey_1", "inchikey_2", dtype=str)
    .require("type", "key", dtype=str)
    .require("value", dtype=float)
    .reserve("sample", dtype=int)
    .strict()
).build()


def _to_long_form(self: SimilarityDfShortForm, kind: str, key: str) -> SimilarityDfLongForm:
    if kind not in ["phi", "psi"]:
        raise ValueError(f"'type' should be 'phi' or 'psi', not {kind}")
    rows = []
    for i in range(len(self)):
        for j in range(0, i + 1):
            v = self.iat[i, j]
            rows.append(
                pd.Series(
                    dict(
                        inchikey_1=self.index[i],
                        inchikey_2=self.columns[j],
                        type=kind,
                        key=key,
                        value=v,
                    )
                )
            )
    return SimilarityDfLongForm(rows)


SimilarityDfShortForm.to_long_form = _to_long_form


ScoreDf = (
    TypedDfs.typed("InputScoreFrame")
    .require("inchikey", "score_name", dtype=str)
    .require("score_value", dtype=float)
).build()


EnrichmentDf = (
    TypedDfs.typed("EnrichmentFrame")
    .require("predicate", "object", "key", "source", dtype=str)
    .require("score_name", dtype=str)
    .require("value", "inverse", dtype=float)
    .reserve("sample", dtype=int)
).build()


ConcordanceDf = (
    TypedDfs.typed("ConcordanceDf")
    .require("phi", "psi", dtype=str)
    .require("tau", dtype=float)
    .reserve("sample", dtype=int)
).build()


PsiProjectedDf = (
    TypedDfs.typed("PsiProjectedDf")
    .require("psi", dtype=str)
    .require("inchikey", dtype=str)
    .require("x", "y", dtype=float)
    .reserve("color", "marker", dtype=str)
).build()
