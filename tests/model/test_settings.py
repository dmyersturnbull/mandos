import pytest
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.settings import Settings

from .. import get_test_resource


class TestSettings:
    def test_settings(self):
        toml = NestedDotDict.read_toml(get_test_resource("settings.toml"))
        x = Settings.load(toml)
        assert str(x.chembl_cache_path) == "~"
        assert x.chembl_n_tries == 100
        assert not x.chembl_fast_save
        assert x.chembl_timeout_sec == 0

    def test_empty(self):
        toml = NestedDotDict.read_toml(get_test_resource("settings-empty.toml"))
        x = Settings.load(toml)
        # TODO


if __name__ == "__main__":
    pytest.main()
