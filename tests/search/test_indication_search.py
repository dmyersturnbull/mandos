import pytest

from mandos.cli import Commands, What

from . import get_test_resource


class TestIndicationSearch:
    def test_find(self):
        df, triples = Commands.search_for(What.trial, get_test_resource("inchis.txt"), None)
        assert len(df) == 6
        assert len(triples) == 6
        assert {t.compound_name.lower() for t in triples} == {"alprazolam"}
        assert {t.object_id for t in triples} == {
            "D012559",
            "D016584",
            "D003704",
            "D001008",
            "D001007",
            "D003866",
        }
        assert {t.object_name.lower() for t in triples} == {
            "schizophrenia",
            "panic disorder",
            "dementia",
            "anxiety",
            "depressive disorder",
            "anxiety disorders",
        }
        assert {t.predicate for t in triples} == {"phase-4 indication", "phase-3 indication"}

    def test_cocaine_hcl(self):
        df, triples = Commands.search_for(What.trial, ["CHEMBL529437"], None)
        assert len(df) == 1
        assert len(triples) == 1
        assert triples[0].compound_name.lower() == "cocaine"
        assert triples[0].compound_id == "CHEMBL370805"
        assert triples[0].object_id == "D000758"
        assert triples[0].object_name == "Anesthesia"
        assert triples[0].predicate == "phase-4 indication"


if __name__ == "__main__":
    pytest.main()
