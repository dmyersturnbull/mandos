"""
Definitions of input types for analysis.
"""

from typing import Optional, Sequence

import numpy as np
import pandas as pd
from pocketutils.core.exceptions import XValueError
from typeddfs import AffinityMatrixDf, TypedDfs


def _to_long_form(self: AffinityMatrixDf, kind: str, key: str):
    if kind not in ["phi", "psi"]:
        raise XValueError(f"'type' should be 'phi' or 'psi', not {kind}")
    df = self.long_form()
    df = df.rename(columns=dict(row="inchikey_1", column="inchikey_2"))
    df["type"] = kind
    df["key"] = key
    return SimilarityDfLongForm.convert(df)


def _to_short_form(self: pd.DataFrame):
    df = self[["inchikey_1", "inchikey_2", "value"]]
    df = df.pivot(index="inchikey_1", columns="inchikey_2")
    df = df.rename(columns=dict(inchikey_2="column"))
    return SimilarityDfShortForm.convert(df)


def _of_constant(self, inchikeys: Sequence[str], score_name: str, score_val: np.float64 = 1.0):
    df = pd.DataFrame([inchikeys], columns=["inchikey"])
    df["score_name"] = score_name
    df["score_val"] = score_val
    return self.__class__.convert(df)


def _makes_sense(df: pd.DataFrame) -> Optional[str]:
    bad_keys = set()
    for k in df["key"].unique():
        x = df[df["key"] == k]["type"].unique().tolist()
        if len(x) > 1:
            bad_keys.add(k)
    if len(bad_keys) > 0:
        return f"These keys are defined for more than one 'type': {bad_keys}"
    return None


SimilarityDfLongForm = (
    TypedDfs.typed("SimilarityDfLongForm")
    .require("inchikey_1", "inchikey_2", dtype=str)
    .require("type", "key", dtype=str)
    .require("value", dtype=np.float64)
    .add_methods(to_short_form=_to_short_form)
    .verify(_makes_sense)
    .strict()
    .secure()
).build()


def _cross(cls, phi: SimilarityDfLongForm, psi: SimilarityDfLongForm):
    phi = phi.vanilla().rename(columns=dict(key="phi", value="phi_value")).drop("type", axis=1)
    psi = psi.vanilla().rename(columns=dict(key="psi", value="psi_value")).drop("type", axis=1)
    df = pd.merge(phi, psi, on=["inchikey_1", "inchikey_2"])
    return cls.convert(df)


PhiPsiSimilarityDfLongForm = (
    TypedDfs.typed("PhiPsiSimilarityDfLongForm")
    .require("inchikey_1", "inchikey_2", dtype=str)
    .require("phi", "psi", dtype=str)
    .require("phi_value", "psi_value", dtype=np.float64)
    .add_classmethods(cross=_cross)
    .strict()
    .secure()
).build()


SimilarityDfShortForm = (
    TypedDfs.affinity_matrix("SimilarityDfShortForm")
    .dtype(np.float64)
    .add_methods(to_long_form=_to_long_form)
    .secure()
).build()


ScoreDf = (
    TypedDfs.typed("ScoreDf")
    .require("inchikey", "score_name", dtype=str)
    .require("score_value", dtype=np.float64)
    .add_methods(of_constant=_of_constant)
    .strict(cols=False)
    .secure()
).build()


EnrichmentDf = (
    TypedDfs.typed("EnrichmentDf")
    .require("predicate", "object", "key", dtype=str)
    .require("score_name", dtype=str)
    .require("value", "inverse", dtype=np.float64)
    .reserve("sample", dtype=int)
    .strict()
    .secure()
).build()


ConcordanceDf = (
    TypedDfs.typed("ConcordanceDf")
    .require("phi", "psi", dtype=str)
    .require("tau", dtype=np.float64)
    .reserve("sample", dtype=int)
    .strict()
    .secure()
).build()


PsiProjectedDf = (
    TypedDfs.typed("PsiProjectedDf")
    .require("psi", dtype=str)
    .require("inchikey", dtype=str)
    .require("x", "y", dtype=np.float64)
    .reserve("color", "marker", dtype=str)
    .strict()
    .secure()
    .hash(file=True)
).build()
