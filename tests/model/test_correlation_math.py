import pytest
import numpy as np

from mandos.model.correlation_math import *

from .. import get_test_resource


class TestAffinityMatrix:
    def test_read(self):
        df = AffinityMatrix.read_csv(get_test_resource("affinity_mx.csv"))
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]

    def test_jaccard(self):
        items = {"cocaine": {"a", "b", "c"}, "gabapentin": {"a", "b"}}
        df = AffinityMatrix.from_function(items, AffinityFunctions.jaccard())
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]
        assert df.values.tolist() == [[1, 2 / 3], [2 / 3, 1]]

    def test_minkowski_1_1(self):
        items = {"cocaine": [1, 2], "gabapentin": [1, 2]}
        df = AffinityMatrix.from_function(items, AffinityFunctions.negative_minkowski(1))
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]
        assert df.values.tolist() == [[0, 0], [0, 0]]

    def test_minkowski_1_2(self):
        items = {"cocaine": [1, 2], "gabapentin": [2, 1]}
        df = AffinityMatrix.from_function(items, AffinityFunctions.negative_minkowski(1))
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]
        assert df.values.tolist() == [[0, -2], [-2, 0]]

    def test_minkowski_2(self):
        items = {"cocaine": [1, 3], "gabapentin": [3, 1]}
        df = AffinityMatrix.from_function(items, AffinityFunctions.negative_minkowski(2))
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]
        assert df.values.tolist() == [[0, -np.sqrt(8)], [-np.sqrt(8), 0]]

    def test_minkowski_0(self):
        items = {"cocaine": [1, 2], "gabapentin": [2, 1]}
        df = AffinityMatrix.from_function(items, AffinityFunctions.negative_minkowski(0))
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]
        assert df.values.tolist() == [[0, -2], [-2, 0]]

    def test_minkowski_inf(self):
        items = {"cocaine": [1, 4], "gabapentin": [2, 1]}
        df = AffinityMatrix.from_function(
            items, AffinityFunctions.negative_minkowski(float("infinity"))
        )
        assert df.rows == ["cocaine", "gabapentin"]
        assert df.cols == ["cocaine", "gabapentin"]
        assert df.values.tolist() == [[0, -3], [-3, 0]]

    def test_pairs(self):
        df = AffinityMatrix.read_csv(get_test_resource("affinity_mx.csv"))
        dct = df.all_pairs()
        assert dct == {
            ("cocaine", "cocaine"): 0.2,
            ("gabapentin", "gabapentin"): 0.2,
            ("cocaine", "gabapentin"): 0.1,
        }

    def test_non_self_pairs(self):
        df = AffinityMatrix.read_csv(get_test_resource("affinity_mx.csv"))
        dct = df.non_self_pairs()
        assert dct == {("cocaine", "gabapentin"): 0.1}


if __name__ == "__main__":
    pytest.main()
