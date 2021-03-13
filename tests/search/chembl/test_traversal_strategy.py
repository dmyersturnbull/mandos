import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.model.chembl_support.chembl_target_graphs import ChemblTargetGraphFactory
from mandos.model.chembl_support.chembl_targets import TargetFactory
from mandos.search.chembl.target_traversal import TargetTraversalStrategies

factory = TargetFactory(Chembl)
graph_factory = ChemblTargetGraphFactory.create(Chembl, factory)


class TestTargetTraversalStrategy1:
    # def test_gabaa(self):
    #    target = TargetFactory.find("CHEMBL2109243", Chembl)
    #    found = TargetTraversalStrategies.strategy1(Chembl).traverse(target)
    #    assert [f.chembl for f in found] == ["CHEMBL2093872"]

    def test_5ht2b(self):
        target = factory.find("CHEMBL1833")
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(
            graph_factory.at_target(target)
        )
        assert [f.chembl for f in found] == ["CHEMBL2096904"]

    def test_5ht2bc_sel_group(self):
        target = factory.find("CHEMBL2111466")
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(
            graph_factory.at_target(target)
        )
        assert [f.chembl for f in found] == ["CHEMBL2096904"]

    def test_mu_or(self):
        target = factory.find("CHEMBL233")
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(
            graph_factory.at_target(target)
        )
        assert [f.chembl for f in found] == ["CHEMBL2095181"]


if __name__ == "__main__":
    pytest.main()
