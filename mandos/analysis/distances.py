"""
Calculations of overlap (similarity) between annotation sets.
"""
import abc
import enum
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Collection, Sequence, Type, Union

import decorateme
import numpy as np
import pandas as pd
from pocketutils.core.chars import Chars
from pocketutils.core.enums import CleverEnum
from pocketutils.tools.unit_tools import UnitTools
from typeddfs.df_errors import HashFileMissingError

from mandos.analysis import AnalysisUtils as Au
from mandos.analysis.io_defns import SimilarityDfLongForm, SimilarityDfShortForm
from mandos.model.hit_dfs import HitDf
from mandos.model.hits import AbstractHit
from mandos.model.utils import unlink

# note that most of these math functions are much faster than their numpy counterparts
# if we're not broadcasting, it's almost always better to use them
# some are more accurate, too
# e.g. we're using fsum rather than sum
from mandos.model.utils.setup import logger


@decorateme.auto_repr_str()
class MatrixCalculator(metaclass=abc.ABCMeta):
    def __init__(self, *, min_compounds: int, min_nonzero: int, min_hits: int):
        self.min_compounds = min_compounds
        self.min_nonzero = min_nonzero
        self.min_hits = min_hits

    def calc_all(self, hits: Path, to: Path, *, keep_temp: bool = False) -> SimilarityDfLongForm:
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
        if self.i % 20000 == 0:
            self.log("info")

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

    def __repr__(self):
        return f"{self.__class__.__name__}({self.i}/{self.n})"

    def __str__(self):
        return repr(self)


class JPrimeMatrixCalculator(MatrixCalculator):
    def calc_all(self, path: Path, to: Path, *, keep_temp: bool = False) -> SimilarityDfLongForm:
        hits = HitDf.read_file(path).to_hits()
        key_to_hit = Au.hit_multidict(hits, "search_key")
        logger.notice(f"Calculating J on {len(key_to_hit):,} keys from {len(hits):,} hits")
        deltas, files, good_keys = [], [], {}
        for key, key_hits in key_to_hit.items():
            key: str = key
            key_hits: Sequence[AbstractHit] = key_hits
            n_compounds_0 = len({k.origin_inchikey for k in key_hits})
            part_path = self._path_of(path, key)
            n_compounds_in_mx = None
            n_nonzero = None
            df = None
            if part_path.exists():
                try:
                    df = SimilarityDfLongForm.read_file(
                        part_path, file_hash=False
                    )  # TODO: file_hash=True
                    logger.warning(f"Results for key {key} already exist ({len(df):,} rows)")
                    n_compounds_in_mx = len(df["inchikey_1"].unique())
                except HashFileMissingError:
                    logger.error(f"Extant results for key {key} appear incomplete; restarting")
                    logger.opt(exception=True).debug(f"Hash error for {key}")
                    unlink(part_path)
                    # now let it go into the next block -- calculate from scratch
            if n_compounds_0 >= self.min_compounds:
                t1 = time.monotonic()
                df: SimilarityDfShortForm = self.calc_one(key, key_hits)
                t2 = time.monotonic()
                deltas.append(t2 - t1)
                df = df.to_long_form(kind="psi", key=key)
                n_compounds_in_mx = len(df["inchikey_1"].unique())
                df.write_file(part_path)
                logger.debug(f"Wrote results for {key} to {part_path}")
            if df is not None:
                n_nonzero = len(df[df["value"] > 0])
            if n_compounds_in_mx < self.min_compounds:
                logger.warning(
                    f"Key {key} has {n_compounds_in_mx:,} < {self.min_compounds:,} compounds; skipping"
                )
            elif len(key_hits) < self.min_hits:
                logger.warning(
                    f"Key {key} has {len(key_hits):,} < {self.min_hits:,} hits; skipping"
                )
            elif n_nonzero is not None and n_nonzero < self.min_nonzero:
                logger.warning(
                    f"Key {key} has {n_nonzero:,} < {self.min_nonzero:,} nonzero pairs; skipping"
                )  # TODO: percent nonzero?
            else:
                files.append(part_path)
                good_keys[key] = n_compounds_in_mx
            del df
        logger.debug(f"Concatenating {len(files):,} files")
        df = SimilarityDfLongForm(
            pd.concat(
                [SimilarityDfLongForm.read_file(self._path_of(path, k)) for k in good_keys.keys()]
            )
        )
        logger.notice(f"Included {len(good_keys):,} keys: {', '.join(good_keys.keys())}")
        quartiles = {}
        for k, v in good_keys.items():
            vals = df[df["key"] == k]["value"]
            qs = {x: vals.quantile(x) for x in [0, 0.25, 0.5, 0.75, 1]}
            quartiles[k] = list(qs.values())
            logger.info(f"Key {k} has {v:,} compounds and {len(key_to_hit[k]):,} hits")
            logger.info(
                f"    {k} {Chars.fatright} unique values = {len(vals.unique())} unique values"
            )
            logger.info(f"    {k} {Chars.fatright} quartiles: " + " | ".join(qs.values()))
        df = df.set_attrs(
            dict(
                keys={
                    k: dict(compounds=v, hits=len(key_to_hit[k]), quartiles=quartiles[k])
                    for k, v in good_keys.items()
                }
            )
        )
        df.write_file(to, attrs=True, file_hash=True)
        logger.notice(f"Wrote {len(df):,} rows to {to}")
        if not keep_temp:
            for k in key_to_hit.keys():
                unlink(self._path_of(path, k))
        return df

    def calc_one(self, key: str, hits: Sequence[AbstractHit]) -> SimilarityDfShortForm:
        ik2hits = Au.hit_multidict(hits, "origin_inchikey")
        logger.info(f"Calculating J on {key} for {len(ik2hits):,} compounds and {len(hits):,} hits")
        data = defaultdict(dict)
        inf = _Inf(n=int(len(ik2hits) * (len(ik2hits) - 1) / 2))
        for (c1, hits1) in ik2hits.items():
            for (c2, hits2) in ik2hits.items():
                if inf.is_used(c1, c2):
                    continue
                z = 1 if c1 == c2 else self._j_prime(key, hits1, hits2)
                data[c1][c2] = z
                inf.got(c1, c2, z)
        inf.log("success")
        return SimilarityDfShortForm.from_dict(data)

    def _path_of(self, path: Path, key: str):
        return path.parent / f".{path.name}-{key}.tmp.feather"

    def _j_prime(
        self, key: str, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]
    ) -> float:
        if len(hits1) == 0 or len(hits2) == 0:
            return 0
        sources = {h.data_source for h in hits1}.intersection({h.data_source for h in hits2})
        if len(sources) == 0:
            return float("NaN")
        values = [
            self._jx(
                key,
                [h for h in hits1 if h.data_source == source],
                [h for h in hits2 if h.data_source == source],
            )
            for source in sources
        ]
        return float(math.fsum(values) / len(values))

    def _jx(
        self, key: str, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]
    ) -> float:
        # TODO -- for testing only
        # TODO: REMOVE ME!
        if key in ["core.chemidplus.effects", "extra.chemidplus.specific-effects"]:
            hits1 = [h.copy(weight=math.pow(10, -h.weight)) for h in hits1]
            hits2 = [h.copy(weight=math.pow(10, -h.weight)) for h in hits2]
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
    def create(
        cls,
        algorithm: Union[str, MatrixAlg],
        *,
        min_compounds: int,
        min_nonzero: int,
        min_hits: int,
    ) -> MatrixCalculator:
        return MatrixAlg.of(algorithm).clazz(
            min_compounds=min_compounds, min_nonzero=min_nonzero, min_hits=min_hits
        )


__all__ = ["MatrixCalculator", "JPrimeMatrixCalculator", "MatrixCalculation", "MatrixAlg"]
