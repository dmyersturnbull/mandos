from dataclasses import dataclass

import pytest

from mandos.model.hit_dfs import HitDf
from mandos.model.hits import AbstractHit

from .. import get_test_resource


@dataclass(frozen=True, order=True, repr=True)
class _SimpleHit(AbstractHit):
    """"""


class TestHits:
    def test(self):
        df = HitDf.read_file(get_test_resource("chembl_atc.csv"))
        hits = df.to_hits(df)
        assert len(hits) == 10
        df2 = HitDf.from_hits(hits)
        assert len(df2) == 10


if __name__ == "__main__":
    pytest.main()
