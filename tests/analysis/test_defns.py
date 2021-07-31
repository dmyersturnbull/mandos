import pytest
from pocketutils.core.dot_dict import NestedDotDict

from mandos.analysis.io_defns import *

from .. import get_test_resource


class TestIoDefns:
    def test_read_short_form(self):
        df = SimilarityDfShortForm.read_file(get_test_resource("shortform-matrix.csv"))
        assert len(df) == 3
        long = df.to_long_form("phi", "phi")
        assert len(long) == 6


if __name__ == "__main__":
    pytest.main()
