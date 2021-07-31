import pytest
from pocketutils.core.dot_dict import NestedDotDict

from mandos.analysis.io_defns import *
from mandos.analysis.prepping import MatrixPrep

from .. import get_test_resource


class TestPrep:
    def test_matrix_prep(self):
        df = MatrixPrep("phi").from_files([get_test_resource("shortform-matrix.csv")])
        assert len(df) == 6
        assert df["key"].unique().tolist() == ["shortform-matrix"]
        assert df["type"].unique().tolist() == ["phi"]


if __name__ == "__main__":
    pytest.main()
