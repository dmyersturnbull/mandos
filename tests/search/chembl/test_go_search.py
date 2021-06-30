import pytest

from mandos.cli import Commands
from mandos.search.chembl.go_search import GoType, GoSearch

from .. import get_test_resource


class TestGoSearch:
    def test_find(self):
        GoSearch()
        df, triples = Commands.go_search(get_test_resource("inchis.txt"), GoType.function)
        assert len(df) == 20
        assert len(triples) == 20
        # TODO not very complete
        assert {t.compound_name.lower() for t in triples} == {"alprazolam"}
        assert {t.pred for t in triples} == {"has GO function term"}


if __name__ == "__main__":
    pytest.main()
