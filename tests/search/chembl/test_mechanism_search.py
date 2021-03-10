import pytest

from mandos.cli import Commands

from .. import get_test_resource


class TestMechanismSearch:
    def test_find(self):
        df, triples = Commands.moa(get_test_resource("inchis.txt"))
        assert len(df) == 1
        assert len(triples) == 1
        assert triples[0].compound_name.lower() == "alprazolam"
        # CHEMBL2109244 is GABA-A receptor; agonist GABA site
        assert triples[0].compound_id == "CHEMBL661"
        assert triples[0].object_id == "CHEMBL2093872"
        assert triples[0].predicate == "positive allosteric modulator"


if __name__ == "__main__":
    pytest.main()
