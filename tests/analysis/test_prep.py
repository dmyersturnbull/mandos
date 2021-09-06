import pytest

from mandos.analysis.prepping import MatrixPrep

from .. import get_test_resource


class TestPrep:
    def test_matrix_prep(self):
        prep = MatrixPrep("phi", normalize=False, log=False, invert=False)
        df = prep.from_files([get_test_resource("analysis", "shortform-matrix.csv")])
        assert len(df) == 6
        assert df["key"].unique().tolist() == ["shortform-matrix"]
        assert df["type"].unique().tolist() == ["phi"]


if __name__ == "__main__":
    pytest.main()
