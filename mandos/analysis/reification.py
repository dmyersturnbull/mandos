"""
Tool to export reified mandos triples.
"""
from typing import Sequence, Generator

from mandos.model.hits import AbstractHit, Triple


class ReifiedExporter:
    def reify(self, hits: Sequence[AbstractHit]) -> Generator[Triple, None, None]:
        for h in hits:
            yield from h.reify()


__all__ = ["ReifiedExporter"]
