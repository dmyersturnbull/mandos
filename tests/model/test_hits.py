from dataclasses import dataclass

import pytest

from mandos.model.hits import HitFrame, AbstractHit, Pair, Triple


@dataclass(frozen=True, order=True, repr=True)
class _SimpleHit(AbstractHit):
    """"""


class TestHits:
    def test(self):
        hit = AbstractHit()

        mp = Mappings.from_resource("@targets_neuro.regexes")
        assert mp.get("Dopamine D3 receptor") == ["Dopamine 2/3/4 receptor", "D_{2/3/4}"]
        assert mp.get("Cytochrome P450 2A6") == ["Cytochrome P450 2", "CYP2"]


if __name__ == "__main__":
    pytest.main()
