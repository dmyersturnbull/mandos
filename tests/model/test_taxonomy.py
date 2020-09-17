from pathlib import Path

import pandas as pd
import pytest

from mandos import get_resource

# noinspection PyUnresolvedReferences
from mandos.model.taxonomy import Taxon, Taxonomy, _Taxon


class TestFind:
    def test_find(self):
        tax = Taxonomy.load(7742)
        assert tax.roots == [Taxon(7742, "Vertebrata", None, set())]
        assert tax[7742] is not None
        assert tax[7742].name == "Vertebrata"
        assert tax[7742].parent is None
        assert tax[117571].id == 117571
        assert tax[117571].name == "Euteleostomi"
        assert tax[10116].name == "Rattus norvegicus"
        assert tax["Rattus norvegicus"].id == 10116
        assert tax["Rattus norvegicus"].name == "Rattus norvegicus"
        assert tax["rattus norvegicus"].id == 10116
        assert tax["rattus norvegicus"].name == "Rattus norvegicus"
        assert tax["Euteleostomi"].parent.id == 11757
        assert [c.id for c in tax["Euteleostomi"].children] == [7898, 8287]
        with pytest.raises(KeyError):
            assert tax["asdfsadf"]
        with pytest.raises(KeyError):
            assert tax[13745754745745]
        with pytest.raises(KeyError):
            assert tax["11757"]
        assert tax.get("asdfsadf") is None
        assert tax.get(13745754745745) is None
        assert tax.get("Euteleostomi").id == 117571
        assert tax.get(117571).id == 117571
        assert 117571 in tax
        assert 13745754745745 not in tax
        assert "Euteleostomi" in tax
        assert "asdfsadf" not in tax

    def test_empty(self):
        tax = Taxonomy({}, {})
        assert len(tax) == 0
        assert tax.roots == []

    def test_root_leaf(self):
        taxon = Taxon(1, "abc", None, set())
        tax = Taxonomy.from_list([taxon])
        assert len(tax) == 1
        assert tax.roots == [taxon]
        assert tax.leaves == [taxon]

    def test_double(self):
        a = _Taxon(1, "a", None, set())
        b = _Taxon(2, "b", a, set())
        a.add_child(b)
        tax = Taxonomy.from_list([a, b])
        assert len(tax) == 2
        assert tax.roots == [a]
        assert tax.leaves == [b]
        assert set(tax.taxa) == {a, b}

    def test_sort(self):
        a = _Taxon(10, "z", None, set())
        b = _Taxon(2, "a", a, set())
        c = _Taxon(2, "b", a, set())
        assert c < a, f"{c} > {a}"
        assert a < c < b, f"{a} vs {b} vs {c}"


if __name__ == "__main__":
    pytest.main()
