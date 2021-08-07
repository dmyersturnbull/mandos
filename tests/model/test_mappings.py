import pytest

from mandos.model.utils.mappings import Mappings


class TestMappings:
    def test(self):
        mp = Mappings.from_resource("@targets_neuro.regexes")
        assert mp.get("Dopamine D3 receptor") == ["Dopamine 2/3/4 receptor", "D_{2/3/4}"]
        assert mp.get("Cytochrome P450 2A6") == ["Cytochrome P450 2", "CYP2"]


if __name__ == "__main__":
    pytest.main()
