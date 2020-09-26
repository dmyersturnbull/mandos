import pytest
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.settings import Settings

from .. import get_test_resource


class TestSettings:
    def test_settings(self):
        toml = NestedDotDict.read_toml(get_test_resource("settings.toml"))
        x = Settings.load(toml)
        assert x.taxon == 1111
        assert x.min_pchembl == 15
        assert x.min_confidence_score == 2
        assert x.min_phase == 0
        assert str(x.cache_path) == "~"
        assert x.n_retries == 100
        assert not x.fast_save
        assert x.timeout_sec == 0

    def test_empty(self):
        toml = NestedDotDict.read_toml(get_test_resource("settings-empty.toml"))
        x = Settings.load(toml)
        assert x.min_phase == 3


if __name__ == "__main__":
    pytest.main()
