from dataclasses import dataclass

import pytest

from mandos.model.hit_dfs import HitUtils
from mandos.model.hits import AbstractHit, HitFrame

from .. import get_test_resource


@dataclass(frozen=True, order=True, repr=True)
class _SimpleHit(AbstractHit):
    """"""


class TestHits:
    def test(self):
        df = HitFrame.read_file(get_test_resource("chembl_atc.csv"))
        hits = HitUtils.df_to_hits(df)
        assert len(hits) == 10
        df2 = HitUtils.hits_to_df(hits)
        assert len(df2) == 10


if __name__ == "__main__":
    pytest.main()
