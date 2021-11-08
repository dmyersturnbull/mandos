"""
Calculations of overlap (similarity) between annotation sets.
"""
import abc
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Collection, Mapping, Optional, Sequence, Type, Union

import decorateme
import numpy as np
from pocketutils.core.chars import Chars
from pocketutils.core.enums import CleverEnum
from pocketutils.core.exceptions import XValueError
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


class _Inf:
    def __init__(self, n: int):
        self.n = n
        self.used, self.t0, self.nonzeros = set(), time.monotonic(), 0

    def is_used(self, c1: str, c2: str) -> bool:
        return (c1, c2) in self.used or (c2, c1) in self.used

    def got(self, c1: str, c2: str, z: float) -> None:
        self.used.add((c1, c2))
        self.nonzeros += int(c1 != c2 and not np.isnan(z) and 0 < z < 1)
        if self.i % 1000 == 0:
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


@decorateme.auto_repr_str()
class MatrixCalculator(metaclass=abc.ABCMeta):
    def __init__(
        self,
        *,
        min_compounds: int,
        min_nonzero: int,
        min_hits: int,
        exclude: Optional[Collection[str]] = None,
    ):
        self.min_compounds = min_compounds
        self.min_nonzero = min_nonzero
        self.min_hits = min_hits
        self.exclude = set() if exclude is None else exclude

    def calc_all(self, hits: Path, to: Path, *, keep_temp: bool = False) -> SimilarityDfLongForm:
        raise NotImplemented()


class JPrimeMatrixCalculator(MatrixCalculator):
    def calc_all(self, path: Path, to: Path, *, keep_temp: bool = False) -> SimilarityDfLongForm:
        hits = self._read_hits(path)
        key_to_hit = Au.hit_multidict(hits, "search_key")
        logger.notice(f"Calculating J on {len(key_to_hit):,} keys from {len(hits):,} hits")
        good_keys = {}
        for key, key_hits in key_to_hit.items():
            key_hits: Sequence[AbstractHit] = key_hits
            n_compounds_0 = len({k.origin_inchikey for k in key_hits})
            part_path = self._part_path(to, key)
            df = None
            if part_path.exists():
                df = self._read_part(key, part_path)
            if df is None and n_compounds_0 >= self.min_compounds:
                df = self._calc_partial(key, key_hits)
                df.write_file(part_path, attrs=True, file_hash=True, mkdirs=True)
                logger.debug(f"Wrote results for {key} to {part_path}")
            if df is not None and self._should_include(df):
                good_keys[key] = part_path
            if df is not None:
                del df
        big_df = self._concat_parts(good_keys)
        big_df.write_file(to, attrs=True, file_hash=True, mkdirs=True)
        logger.notice(f"Wrote {len(big_df):,} rows to {to}")
        attrs_path = to.parent / (to.name + ".attrs.json")
        logger.sucess(f"Finished -- see {attrs_path} for statistics")
        if not keep_temp:
            for k in good_keys:
                unlink(self._part_path(to, k))

    def _read_hits(self, path: Path) -> Sequence[AbstractHit]:
        hits = HitDf.read_file(path)
        keys = hits["search_key"].unique()
        bad_excludes = [e for e in self.exclude if e not in keys]
        if len(bad_excludes) > 0:
            logger.error(f"Keys to exclude are not in the input file: {', '.join(bad_excludes)}")
        for key in keys:
            if key not in self.exclude:
                dfx = hits[hits["search_key"] == key]
                negatives = dfx[dfx["weight"] <= 0]
                if len(negatives) > 0:
                    logger.error(f"{len(negatives)} / {len(dfx):,} hits for {key} are nonpositive")
        return [h for h in hits.to_hits() if h.search_key not in self.exclude and h.weight > 0]

    def _calc_partial(self, key: str, key_hits: HitDf) -> SimilarityDfLongForm:
        df = self.calc_one(key, key_hits).to_long_form(kind="psi", key=key)
        return df.set_attrs(
            key=key,
            quartiles=[float(df["value"].quantile(x)) for x in [0, 0.25, 0.5, 0.75, 1]],
            n_hits=len(key_hits),
            n_values=len(df["value"].unique()),
            n_compounds=len(df["inchikey_1"].unique()),
            n_real=len(df[(df["value"].notna()) & (df["value"] > 0) & (df["value"] < 1)]),
        )

    def _should_include(self, df: SimilarityDfLongForm) -> bool:
        key = df.attrs["key"]
        reqs = dict(n_compounds=self.min_compounds, n_hits=self.min_hits, n_real=self.min_nonzero)
        for a, mn in reqs.items():
            v = df.attrs[a]
            if v < mn:
                logger.warning(f"Key {key}: {a} = {v:,} < {mn:,}")
                return False
        return True

    def _read_part(self, key: str, part_path: Path) -> Optional[SimilarityDfLongForm]:
        try:
            df = SimilarityDfLongForm.read_file(part_path, file_hash=True, attrs=True)
            logger.warning(f"Results for key {key} already exist ({len(df):,} rows)")
            return df
        except HashFileMissingError:
            logger.error(f"Extant results for key {key} appear incomplete; restarting")
            logger.opt(exception=True).debug(f"Hash error for {key}")
            unlink(part_path)
        return None  #  calculate from scratch

    def _concat_parts(self, keys: Mapping[str, Path]):
        logger.notice(f"Included {len(keys):,} keys: {', '.join(keys)}")
        dfs = []
        for key, pp in keys.items():
            df = SimilarityDfLongForm.read_file(pp, attrs=True)
            dfs.append(df)
        return SimilarityDfLongForm.of(dfs, keys=keys)

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

    def _part_path(self, path: Path, key: str):
        return path.parent / f".{path.name}-{key}.tmp.feather"

    def _j_prime(
        self, key: str, hits1: Collection[AbstractHit], hits2: Collection[AbstractHit]
    ) -> float:
        if len(hits1) == len(hits2) == 0:
            return float("NaN")  # TODO: Can this even happen?
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
        if len(hits1) == len(hits2) == 0:
            return float("NaN")  # TODO: impossible, right?
        if len(hits1) == 0 or len(hits2) == 0:
            return 0
        pair_to_weights = Au.weights_of_pairs(hits1, hits2)
        values = []
        for ca, cb in pair_to_weights.values():
            wedge = self._wedge(ca, cb)
            vee = self._vee(ca, cb)
            if vee > 0:
                values.append(wedge / vee)
        return float(math.fsum(values) / len(values))

    def _wedge(self, ca: float, cb: float) -> float:
        return math.sqrt(Au.elle(ca) * Au.elle(cb))

    def _vee(self, ca: float, cb: float) -> float:
        return Au.elle(ca) + Au.elle(cb) - math.sqrt(Au.elle(ca) * Au.elle(cb))


class MatrixAlg(CleverEnum):
    j = ()

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
        exclude: Optional[Collection[str]] = None,
    ) -> MatrixCalculator:
        return MatrixAlg.of(algorithm).clazz(
            min_compounds=min_compounds,
            min_nonzero=min_nonzero,
            min_hits=min_hits,
            exclude=exclude,
        )


__all__ = ["JPrimeMatrixCalculator", "MatrixAlg", "MatrixCalculation", "MatrixCalculator"]
