import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.cli import Commands, Searcher
from mandos.model.apis.chembl_api import ChemblApi
from mandos.search.chembl.indication_search import IndicationSearch

from .. import get_test_resource


class TestIndicationSearch:
    def test_find(self):
        df, triples = Commands.trials(get_test_resource("inchis.txt"))
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
        assert {t.obj.lower() for t in triples} == {
            "schizophrenia",
            "panic disorder",
            "dementia",
            "anxiety",
            "depressive disorder",
            "anxiety disorders",
        }
        assert {t.pred for t in triples} == {"phase-4 indication", "phase-3 indication"}

    def test_cocaine_hcl(self):
        api = ChemblApi.wrap(Chembl)
        df, triples = Searcher(IndicationSearch(api, min_phase=3)).search_for(["CHEMBL529437"])
        assert len(df) == 1
        assert len(triples) == 1
        assert triples[0].compound_name.lower() == "cocaine"
        assert triples[0].compound_id == "CHEMBL370805"
        assert triples[0].object_id == "D000758"
        assert triples[0].obj == "Anesthesia"
        assert triples[0].pred == "phase-4 indication"


if __name__ == "__main__":
    pytest.main()
