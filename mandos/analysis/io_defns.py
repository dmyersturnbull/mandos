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


def _to_long_form(self, kind: str, key: str):
    if kind not in ["phi", "psi"]:
        raise ValueError(f"'type' should be 'phi' or 'psi', not {kind}")
    df = self.long_form()
    df = df.rename(columns=dict(row="inchikey_1", column="inchikey_2"))
    df["type"] = kind
    df["key"] = key
    return SimilarityDfLongForm.convert(df)


def _of_constant(self, inchikeys: Sequence[str], score_name: str, score_val: np.float64 = 1.0):
    df = pd.DataFrame([inchikeys], columns=["inchikey"])
    df["score_name"] = score_name
    df["score_val"] = score_val
    return self.__class__.convert(df)


SimilarityDfLongForm = (
    TypedDfs.typed("SimilarityDfLongForm")
    .require("inchikey_1", "inchikey_2", dtype=str)
    .require("type", "key", dtype=str)
    .require("value", dtype=np.float64)
    .reserve("sample", dtype=int)
    .strict()
).build()

SimilarityDfShortForm = (
    TypedDfs.affinity_matrix("SimilarityDfShortForm")
    .dtype(np.float64)
    .add_methods(to_long_form=_to_long_form)
).build()


ScoreDf = (
    TypedDfs.typed("InputScoreFrame")
    .require("inchikey", "score_name", dtype=str)
    .require("score_value", dtype=np.float64)
    .add_methods(of_constant=_of_constant)
).build()


EnrichmentDf = (
    TypedDfs.typed("EnrichmentFrame")
    .require("predicate", "object", "key", "source", dtype=str)
    .require("score_name", dtype=str)
    .require("value", "inverse", dtype=np.float64)
    .reserve("sample", dtype=int)
).build()


ConcordanceDf = (
    TypedDfs.typed("ConcordanceDf")
    .require("phi", "psi", dtype=str)
    .require("tau", dtype=np.float64)
    .reserve("sample", dtype=int)
).build()


PsiProjectedDf = (
    TypedDfs.typed("PsiProjectedDf")
    .require("psi", dtype=str)
    .require("inchikey", dtype=str)
    .require("x", "y", dtype=np.float64)
    .reserve("color", "marker", dtype=str)
).build()
