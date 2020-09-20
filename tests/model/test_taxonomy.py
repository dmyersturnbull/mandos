import pytest

from mandos import get_resource
from mandos.model.caches import TaxonomyCache
from mandos.model.taxonomy import Taxon, Taxonomy, _Taxon


class TestFind:
    def test_find(self):
        tax = TaxonomyCache(7742).load()
        assert len(tax) == 100670
        assert tax.roots == [Taxon(7742, "Vertebrata", None, set())]
        assert len(tax.roots[0].descendents) == 100669
        assert tax[7742] is not None
        assert tax[7742].name == "Vertebrata"
        assert tax[7742].parent is None
        assert tax[117571].id == 117571
        assert tax[117571].name == "Euteleostomi"
        assert tax[10116].name == "Rattus norvegicus"
        assert 117571 in tax
        assert [c.id for c in tax[117571].children] == [7898, 8287]
        with pytest.raises(KeyError):
            assert tax[3343463643446436347457475]
        assert tax.get(3343463643446436347457475) is None
        assert tax.get(117571).id == 117571
        assert 117571 in tax
        assert 13745754745745 not in tax

    def test_empty(self):
        tax = Taxonomy({})
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
        under = tax.subtree(1)
        assert len(under) == 2
        assert under[1] == a
        assert under[2] == b
        under = tax.subtree(2)
        assert len(under) == 1
        assert under[2] == b

    def test_sort(self):
        a = _Taxon(10, "z", None, set())
        b = _Taxon(2, "a", a, set())
        c = _Taxon(4, "b", a, set())
        assert b < c, f"{b} vs {c}"
        assert b < c < a, f"{a} vs {b} vs {c}"

    def test_real(self):
        path = get_resource("7742.tab.gz")
        tax = Taxonomy.from_path(path)
        assert len(tax) == 100670
        tax = tax.subtree(117571)
        # number from https://www.uniprot.org/taxonomy/117571
        assert len(tax) == 97993


if __name__ == "__main__":
    pytest.main()
