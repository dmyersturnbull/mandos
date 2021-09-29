from collections import Sequence

import pytest

from mandos.entry.api_singletons import Apis
from mandos.model.hits import AbstractHit
from mandos.search.chembl.indication_search import IndicationSearch

from .. import get_test_resource


class TestIndicationSearch:
    def test_find(self):
        search = IndicationSearch(key="indications", api=Apis.Chembl, min_phase=0)
        inchikeys = get_test_resource("inchis.txt").read_text(encoding="utf8").splitlines()
        hits: Sequence[AbstractHit] = search.find_all(inchikeys)
        assert len(hits) == 6
        assert {t.compound_name.lower() for t in hits} == {"alprazolam"}
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
