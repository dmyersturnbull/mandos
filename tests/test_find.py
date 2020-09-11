from pathlib import Path

import pandas as pd
import pytest

from mandos.activity import ActivitySearch
from mandos.taxonomy import Taxonomy


class TestFind:
    def test_find(self):
        df = pd.read_csv(
            Path(__file__).parent.parent / "mandos" / "resources" / "taxonomy-ancestor_7742.tab.gz",
            sep="\t",
        )
        tax = Taxonomy.from_df(df)
        finder = ActivitySearch(tax)
        # CHEMBL370805, cocaine, ZPUCINDJVBIVPJ-LJISPDSOSA-N
        # alprazolam, VREFGVBLTWBCJP-UHFFFAOYSA-N, CHEMBL661
        #found = list(finder.find("CHEMBL661"))
        pass


if __name__ == "__main__":
    pytest.main()
