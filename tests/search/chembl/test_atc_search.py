import pytest

from mandos.cli import Commands

from .. import get_test_resource


class TestAtcs:
    def test_find(self):
        df, triples = Commands.atc(get_test_resource("inchis.txt"))
        assert len(df) == 2
        assert len(triples) == 2
        assert triples[0].compound_name.lower() == "alprazolam"
        assert triples[0].object_name == "ANXIOLYTICS"
        assert triples[0].object_id == "N05B"
        assert triples[1].object_name == "Benzodiazepine derivatives"
        assert triples[1].object_id == "N05BA"
        pass


if __name__ == "__main__":
    pytest.main()
