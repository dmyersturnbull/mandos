import pytest
from chembl_webresource_client.new_client import new_client as _Chembl

from mandos.model.apis.chembl_api import ChemblApi
from mandos.search.chembl.atc_search import AtcSearch
from mandos.model.concrete_hits import AtcHit

from .. import get_test_resource

Chembl = ChemblApi.wrap(_Chembl)


class TestAtcs:
    def test_find(self):
        search = AtcSearch("", {0, 1}, Chembl)
        inchikeys = get_test_resource("inchis.txt").read_text(encoding="utf8").splitlines()
        df = search.find_to_df(inchikeys)
        assert len(df) == 2
        """
        assert len(triples) == 2
        assert triples[0].compound_name.lower() == "alprazolam"
        assert triples[0].obj == "ANXIOLYTICS"
        assert triples[0].object_id == "N05B"
        assert triples[1].obj == "Benzodiazepine derivatives"
        assert triples[1].object_id == "N05BA"
        """


if __name__ == "__main__":
    pytest.main()
