"""
Tool to export reified mandos triples.
"""
from typing import Generator, Sequence

import decorateme

from mandos.model.hits import AbstractHit, Triple


def _camelcase(s: str):
    return "".join(w.title() if i > 0 else w for i, w in enumerate(s.split("_")))


@decorateme.auto_repr_str()
class Reifier:
    def reify(self, hits: Sequence[AbstractHit]) -> Generator[Triple, None, None]:
        for hit in hits:
            yield from self._reify_one(hit)

    def _reify_one(self, hit: AbstractHit) -> Sequence[Triple]:
        uid = hit.universal_id
        state = Triple(uid, "rdf:type", "rdf:statement", None)
        pred = Triple(uid, "rdf:predicate", hit.predicate, None)
        obj = Triple(uid, "rdf:object", hit.object_name, None)
        exclude = {"origin_inchikey", "predicate"}
        # search_key and data_source are included in others
        others = [
            Triple(uid, "mandos:" + _camelcase(field), getattr(hit, field), None)
            for field in hit.fields()
            if field not in exclude
        ]
        return [state, pred, obj, *others]


__all__ = ["Reifier"]
