import pytest

from mandos.cli import Commands, What

from . import get_test_resource


class TestMechanismSearch:
    def test_find(self):
        df, triples = Commands.search_for(What.mechanism, get_test_resource("inchis.txt"), None)
        assert len(df) == 1
        assert len(triples) == 1
        assert triples[0].compound_name == "alprazolam"
        assert triples[0].object_id == "CHEMBL2109224"
        assert triples[0].predicate == "positive allosteric modulator"


if __name__ == "__main__":
    pytest.main()
