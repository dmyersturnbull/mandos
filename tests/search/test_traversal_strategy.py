import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.api import ChemblApi, ChemblEntrypoint
from mandos.model.targets import Target, TargetFactory, TargetType
from mandos.search.target_traversal_strategy import (
    TargetTraversalStrategies,
    TargetTraversalStrategy1,
)

from . import get_test_resource


class TestTargetTraversalStrategy1:
    def test_gabaa(self):
        target = TargetFactory.find("CHEMBL2109243", Chembl)
        found = TargetTraversalStrategies.strategy1(Chembl).traverse(target)
        assert [f.chembl for f in found] == ["CHEMBL2093872"]


if __name__ == "__main__":
    pytest.main()
