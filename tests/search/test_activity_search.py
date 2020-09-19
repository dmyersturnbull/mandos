import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.search.activity_search import ActivitySearch
from mandos.model import ChemblApi
from mandos.model.taxonomy import Taxonomy


class TestFind:
    def test_find(self):
        tax = Taxonomy.load(7742)
        finder = ActivitySearch(ChemblApi.wrap(Chembl), tax)
        # CHEMBL370805, cocaine, ZPUCINDJVBIVPJ-LJISPDSOSA-N
        # alprazolam, VREFGVBLTWBCJP-UHFFFAOYSA-N, CHEMBL661
        found = list(finder.find("CHEMBL661"))
        pass


if __name__ == "__main__":
    pytest.main()
