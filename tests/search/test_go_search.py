import pytest

from mandos.cli import Commands, What

from . import get_test_resource


class TestGoSearch:
    def test_find(self):
        df, triples = Commands.search_for(What.go_fn_moa, get_test_resource("inchis.txt"), None)
        assert len(df) == 20
        assert len(triples) == 20
        # TODO not very complete
        assert {t.compound_name.lower() for t in triples} == {"alprazolam"}
        assert {t.predicate for t in triples} == {"has GO function term"}


if __name__ == "__main__":
    pytest.main()
