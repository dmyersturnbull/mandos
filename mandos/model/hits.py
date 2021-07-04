import dataclasses
import html
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

import pandas as pd
from typeddfs import TypedDfs

from mandos.model import ReflectionUtils

HIT_FIELD_TYPE = frozenset([str, int, float, datetime])


@dataclass(frozen=True, repr=True, order=True)
class Pair:
    """
    Predicate, object pairs.
    """

    pred: str
    obj: str


@dataclass(frozen=True, repr=True, order=True)
class Triple:
    """
    Usually compound, predicate, object.
    """

    sub: str
    pred: str
    obj: str

    @property
    def n_triples(self) -> str:
        """
        Returns a simple text statement in n-triples format.
        """
        s = self.sub
        p = html.escape(self.pred, quote=True)
        o = html.escape(self.obj, quote=True)
        return f'"{s}" "{p}" "{o}" .'


@dataclass(frozen=True, order=True, repr=True)
class AbstractHit:
    """
    An abstract annotation (statement type), which may support additional fields.
    """

    record_id: Optional[str]
    origin_inchikey: str
    matched_inchikey: str
    compound_id: str
    compound_name: str
    predicate: str
    statement: str
    object_id: str
    object_name: str
    value: float
    search_key: str
    search_class: str
    data_source: str
    run_date: datetime
    cache_date: Optional[datetime]
    # is_hit: Optional[bool] = None
    # score: Optional[float] = None
    # x_score_1: Optional[float] = None
    # x_score_2: Optional[float] = None

    @property
    def hit_class(self) -> str:
        return self.__class__.__name__

    @property
    def to_triple(self) -> Triple:
        return Triple(sub=self.origin_inchikey, pred=self.predicate, obj=self.object_name)

    @property
    def to_pair(self) -> Pair:
        return Pair(pred=self.predicate, obj=self.object_name)

    def __hash__(self):
        return hash(self.record_id)

    @property
    def universal_id(self) -> str:
        """
        Gets an identifier (a hex key) that uniquely identifies the record by its unique attributes.
        Does **NOT** distinguish between hits with duplicate information and does **NOT**
        include ``record_id``.

        Returns:
            A 16-character hexadecimal string
        """
        # excluding record_id only because it's not available for some hit types
        # we'd rather immediately see duplicates if the exist
        fields = {
            field
            for field in self.fields()
            if field
            not in {"record_id", "origin_inchikey", "compound_name", "search_key", "search_class"}
        }
        hexed = hex(hash(tuple([getattr(self, f) for f in fields])))
        # remove negative signs -- still unique
        return hexed.replace("-", "").replace("0x", "")

    @classmethod
    def fields(cls) -> Sequence[str]:
        """
        Finds the list of fields in this class by reflection.
        """
        return [f.name for f in dataclasses.fields(cls)]


HitFrame = (
    TypedDfs.typed("HitFrame")
    .require("record_id", dtype=str)
    .require("inchikey", "compound_id", "compound_name", dtype=str)
    .require("predicate", "statement", dtype=str)
    .require("object_id", "object_name", dtype=str)
    .require("search_key", "search_class", "data_source", dtype=str)
    .require("hit_class", dtype=str)
    .require("cache_date", "run_date", dtype=str)
    .reserve("is_hit", dtype=bool)
    .reserve("score", *[f"x_score_{i}" for i in range(1, 10)], dtype=float)
).build()


class HitUtils:
    @classmethod
    def hits_to_df(cls, hits: Sequence[AbstractHit]) -> HitFrame:
        data = []
        for hit in hits:
            x = {f: getattr(hit, f) for f in hit.__class__.fields()}
            x["universal_id"] = hit.universal_id
            x["hit_class"] = hit.hit_class
            data.append(x)
        return HitFrame([pd.Series(x) for x in data])

    @classmethod
    def df_to_hits(cls, self: HitFrame) -> Sequence[AbstractHit]:
        hits = []
        for row in self.iterrows():
            clazz = ReflectionUtils.injection(row.hit_class, AbstractHit)
            # ignore extra columns
            # if cols are missing, let it fail on clazz.__init__
            data = {f: getattr(row, f) for f in self.columns if f in row.__dict__}
            # noinspection PyArgumentList
            hit = clazz(**data)
            hits.append(hit)
        return hits


__all__ = ["AbstractHit", "HitFrame", "Pair", "Triple", "HIT_FIELD_TYPE", "HitUtils"]
