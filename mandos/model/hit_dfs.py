from typing import Sequence

import numpy as np
import pandas as pd
from typeddfs import TypedDfs
from typeddfs.abs_dfs import AbsDf

from mandos.model.concrete_hits import HIT_CLASSES
from mandos.model.hits import AbstractHit
from mandos.model.utils.setup import logger


def _from_hits(cls, hits: Sequence[AbstractHit]) -> AbsDf:
    data = []
    if len(hits) == 0:
        logger.debug(f"No hits")
        return cls.new_df()
    for hit in hits:
        x = {f: getattr(hit, f) for f in hit.__class__.fields()}
        x["universal_id"] = hit.universal_id
        x["hit_class"] = hit.hit_class
        data.append(x)
    return cls.of([pd.Series(x) for x in data])


def _to_hits(self: AbsDf) -> Sequence[AbstractHit]:
    hits = []
    for row in self.itertuples():
        clazz = HIT_CLASSES[row.hit_class]
        # ignore extra columns
        # if cols are missing, let it fail on clazz.__init__
        data = {f: getattr(row, f) for f in clazz.fields()}
        # noinspection PyArgumentList
        hit = clazz(**data)
        hits.append(hit)
    return hits


HitDf = (
    TypedDfs.typed("HitDf")
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
    .add_classmethods(from_hits=_from_hits)
    .add_methods(to_hits=_to_hits)
    .strict(cols=False)
    .secure()
).build()


__all__ = ["HitDf"]
