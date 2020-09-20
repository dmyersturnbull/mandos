import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.model import ChemblApi
from mandos.model.taxonomy import Taxonomy
from mandos.search.atc_search import AtcSearch


class TestAtcs:
    def test_find(self):
        tax = Taxonomy.load(7742)
        finder = AtcSearch(ChemblApi.wrap(Chembl), tax)
        # CHEMBL370805, cocaine, ZPUCINDJVBIVPJ-LJISPDSOSA-N
        # alprazolam, VREFGVBLTWBCJP-UHFFFAOYSA-N, CHEMBL661
        found = list(finder.find("CHEMBL661"))
        pass


if __name__ == "__main__":
    pytest.main()
