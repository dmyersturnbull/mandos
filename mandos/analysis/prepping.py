"""
X.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, Mapping, Sequence, List

import numpy as np
import pandas as pd
from typeddfs import BaseDf
from typeddfs.df_errors import UnsupportedOperationError

from mandos import logger
from mandos.analysis.io_defns import SimilarityDfLongForm, SimilarityDfShortForm
from mandos.entry.searchers import InputFrame
from mandos.model.utils.rdkit_utils import RdkitUtils

T = TypeVar("T", bound=BaseDf)


@dataclass(frozen=True, repr=True)
class MatrixPrep:
    kind: str
    normalize: bool
    log: bool
    invert: bool

    def from_files(self, paths: Sequence[Path]) -> SimilarityDfLongForm:
        dct = {}
        for p in paths:
            key = p.with_suffix("").name
            try:
                dct[key] = SimilarityDfShortForm.read_file(p)
            except (OSError, UnsupportedOperationError, ValueError):
                logger.error(f"Failed to load matrix at {str(p)}")
                raise
        return self.create(dct)

    def create(self, key_to_mx: Mapping[str, SimilarityDfShortForm]) -> SimilarityDfLongForm:
        df = SimilarityDfLongForm(
            pd.concat([mx.to_long_form(self.kind, key) for key, mx in key_to_mx.items()])
        )
        vals = df["value"]
        if self.invert:
            vals = -vals
        if self.normalize:
            mn, mx = vals.min(), vals.max()
            vals = (vals - mn) / (mn - mx)
        if self.log:
            # this is a bit stupid, but calc the log then normalize again
            # we can't take the log before normalization because we might have negative values
            vals = vals.map(np.log10)
            mn, mx = vals.min(), vals.max()
            vals = (vals - mn) / (mn - mx)
        df["value"] = vals
        return SimilarityDfLongForm.convert(df)

    @classmethod
    def ecfp_matrix(cls, df: InputFrame, radius: int, n_bits: int) -> SimilarityDfShortForm:
        # TODO: This is inefficient and long
        indices = range(len(df))
        keys = df["inchikey"]
        on_bits = [
            RdkitUtils.ecfp(c, radius=radius, n_bits=n_bits).list_on for c in df.get_structures()
        ]
        the_rows: List[List[float]] = []
        for i, row_key, row_print in zip(indices, keys, on_bits):
            for j, col_key, col_print in zip(indices, keys, on_bits):
                the_row = []
                if i < j:
                    jaccard = len(row_print.intersection(col_print)) / len(
                        row_print.union(col_print)
                    )
                    the_row.append(jaccard)
                the_rows.append(the_row)
        short = SimilarityDfShortForm(the_rows)
        short["inchikey"] = keys
        short = short.set_index("inchikey")
        short.columns = keys
        return SimilarityDfShortForm.convert(short)


__all__ = ["MatrixPrep"]
