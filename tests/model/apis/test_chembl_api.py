import pytest
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_api import (ChemblApi, ChemblEntrypoint,
                                          ChemblFilterQuery)


class TestChemblApi:
    def test_mocked(self):
        api = ChemblApi.mock({"target": ChemblEntrypoint.mock({"DAT": {"x": ""}})})
        dotdict = NestedDotDict({"x": ""})
        assert api.target is not None
        assert api.target.get("DAT") is not None
        assert isinstance(api.target.get("DAT"), NestedDotDict)
        assert api.target.get("DAT") == dotdict
        with pytest.raises(KeyError):
            assert api.target.get("fasw")
        assert isinstance(api.target.filter(), ChemblFilterQuery)
        assert isinstance(api.target.filter().only([]), ChemblFilterQuery)
        z = list(api.target.filter().only([]))
        assert z == [dotdict]


if __name__ == "__main__":
    pytest.main()
