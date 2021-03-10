import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.model.chembl_support.chembl_targets import TargetFactory
from mandos.search.chembl.target_traversal import (
    TargetTraversalStrategies,
)


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
