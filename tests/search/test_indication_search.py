import pytest

from mandos.cli import Commands, What

from . import get_test_resource


class TestIndicationSearch:
    def test_find(self):
        df, triples = Commands.search_for(What.indication, get_test_resource("inchis.txt"), None)
        assert len(df) == 6
        assert len(triples) == 6
        assert triples[0].compound_name.lower() == "alprazolam"
        assert triples[0].object_id == "D001007"
        assert triples[0].object_name == "Anxiety"
        assert triples[0].predicate == "indicated for"


if __name__ == "__main__":
    pytest.main()
