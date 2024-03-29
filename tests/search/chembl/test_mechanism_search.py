import pytest

from mandos.cli import MandosCli


class TestMechanismSearch:
    def test_find(self):
        """
        df, triples = MandosCli.search_cmds.mechanism(get_test_resource("inchis.txt"))
        assert len(df) == 1
        assert len(triples) == 1
        assert triples[0].compound_name.lower() == "alprazolam"
        # CHEMBL2109244 is GABA-A receptor; agonist GABA site
        assert triples[0].compound_id == "CHEMBL661"
        assert triples[0].object_id == "CHEMBL2093872"
        assert triples[0].pred == "positive allosteric modulator"
        """


if __name__ == "__main__":
    pytest.main()
