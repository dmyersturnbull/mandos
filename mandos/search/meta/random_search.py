from typing import Sequence

from mandos.model.concrete_hits import MetaHit
from mandos.search.meta import MetaSearch


class RandomSearch(MetaSearch[MetaHit]):
    """ """

    def __init__(self, key: str, seed: int, n: int):
        super().__init__(key, seed)
        self.n = n

    def find(self, inchikey: str) -> Sequence[MetaHit]:
        r = str(self.random.randint(0, self.n))  # TODO
        return [
            self._create_hit(
                data_source=self._format_source(),
                c_id=inchikey,
                c_origin=inchikey,
                c_matched=inchikey,
                c_name=inchikey,
                predicate=self._format_predicate(),
                object_id=r,
                object_name=r,
            )
        ]


__all__ = ["RandomSearch"]
