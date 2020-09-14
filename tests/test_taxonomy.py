from pathlib import Path

import pandas as pd
import pytest

from mandos.model.taxonomy import Taxonomy


class TestFind:
    def test_find(self):
        df = pd.read_csv(
            Path(__file__).parent.parent / "mandos" / "resources" / "taxonomy-ancestor_7742.tab.gz",
            sep="\t",
        )
        tax = Taxonomy.from_df(df)
        assert tax[10116] is not None
        assert tax[10116].name == "Rattus norvegicus"
        assert tax["Rattus norvegicus"] is not None
        assert tax["Rattus norvegicus"].name == "Rattus norvegicus"
        assert tax["rattus norvegicus"] is not None
        assert tax["rattus norvegicus"].name == "Rattus norvegicus"


if __name__ == "__main__":
    pytest.main()
