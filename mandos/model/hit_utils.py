from typing import Sequence

import pandas as pd

from mandos.model.hits import AbstractHit, HitFrame
from mandos.model.concrete_hits import HIT_CLASSES


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
        for row in self.itertuples():
            clazz = HIT_CLASSES[row.hit_class]
            # ignore extra columns
            # if cols are missing, let it fail on clazz.__init__
            data = {f: getattr(row, f) for f in clazz.fields()}
            # noinspection PyArgumentList
            hit = clazz(**data)
            hits.append(hit)
        return hits


__all__ = ["HitUtils"]
