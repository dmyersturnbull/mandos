import dataclasses
import html
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

import numpy as np
from typeddfs import TypedDfs

HIT_FIELD_TYPE = frozenset([str, int, float, datetime])


@dataclass(frozen=True, repr=True, order=True)
class KeyPredObj:
    """
    Predicate, object pairs.
    """

    pred: str
    obj: str
    key: str


@dataclass(frozen=True, repr=True, order=True)
class KeyPredObjSource:
    """
    Predicate, object pairs.
    """

    pred: str
    obj: str
    key: str
    source: str

    @property
    def to_key_pred_obj(self) -> KeyPredObj:
        return KeyPredObj(self.pred, self.obj, self.key)


@dataclass(frozen=True, repr=True, order=True)
class Triple:
    """
    Usually compound, predicate, object. Also includes the search key, if meaningful.
    """

    sub: str
    pred: str
    obj: str
    key: Optional[str]

    @property
    def n_triples(self) -> str:
        """
        Returns a simple text statement in n-triples format.
        Includes the key if it's present.
        """
        s = self.sub
        if self.key is None:
            p = html.escape(self.pred, quote=True)
        else:
            p = html.escape(self.key + ":" + self.pred, quote=True)
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
    object_id: str
    object_name: str
    weight: float
    search_key: str
    search_class: str
    data_source: str
    run_date: datetime
    cache_date: Optional[datetime]

    @property
    def hit_class(self) -> str:
        return self.__class__.__name__

    @property
    def to_triple(self) -> Triple:
        return Triple(
            sub=self.origin_inchikey, pred=self.predicate, obj=self.object_name, key=self.search_key
        )

    @property
    def to_key_pred_obj(self) -> KeyPredObj:
        return KeyPredObj(pred=self.predicate, obj=self.object_name, key=self.search_key)

    @property
    def to_key_pred_obj_source(self) -> KeyPredObjSource:
        return KeyPredObjSource(
            pred=self.predicate, obj=self.object_name, key=self.search_key, source=self.data_source
        )

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
        # TODO: cache instead
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
    .require("origin_inchikey", "matched_inchikey", dtype=str)
    .require("predicate", dtype=str)
    .require("object_id", "object_name", dtype=str)
    .require("search_key", "search_class", "data_source", dtype=str)
    .require("hit_class", dtype=str)
    .require("cache_date", "run_date")
    .reserve("inchi", "smiles", dtype=str)
    .reserve("compound_id", "compound_name", dtype=str)
    .reserve("chembl_id", "pubchem_id", dtype=str)
    .reserve("weight", dtype=np.float64)
    .strict(cols=False)
    .secure()
).build()

df = HitFrame.read_excel()

__all__ = ["AbstractHit", "HitFrame", "KeyPredObj", "KeyPredObjSource", "Triple", "HIT_FIELD_TYPE"]
