import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.chembl_api import ChemblApi, ChemblEntrypoint
from mandos.model.targets import Target, TargetFactory, TargetType
from mandos.search.target_traversal_strategy import (
    TargetTraversalStrategies,
    TargetTraversalStrategy1,
)

from . import get_test_resource


class TestTargetTraversalStrategy1:
    # def test_gabaa(self):
    #    target = TargetFactory.find("CHEMBL2109243", Chembl)
    #    found = TargetTraversalStrategies.strategy1(Chembl).traverse(target)
    #    assert [f.chembl for f in found] == ["CHEMBL2093872"]

    def test_5ht2b(self):
        target = TargetFactory.find("CHEMBL1833", Chembl)
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(target)
        assert [f.chembl for f in found] == ["CHEMBL2096904"]

    def test_5ht2bc_sel_group(self):
        target = TargetFactory.find("CHEMBL2111466", Chembl)
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(target)
        assert [f.chembl for f in found] == ["CHEMBL2096904"]

    def test_mu_or(self):
        target = TargetFactory.find("CHEMBL233", Chembl)
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(target)
        assert [f.chembl for f in found] == ["CHEMBL2095181"]


if __name__ == "__main__":
    pytest.main()
