import pytest


class TestActivitySearch:
    def test_find(self):
        """
        df, triples = Commands.binding(get_test_resource("inchis.txt"))
        # TODO double-check
        assert len(df) == 4
        assert len(triples) == 1
        assert triples[0].object_id == "CHEMBL2093872"
        assert triples[0].compound_name.lower() == "alprazolam"
        """


if __name__ == "__main__":
    pytest.main()
