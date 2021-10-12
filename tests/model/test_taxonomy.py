import pytest

from mandos.model.taxonomy import Taxon, Taxonomy, _Taxon
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.model.utils import MandosResources


class TestFind:
    def test_find(self):
        tax = TaxonomyFactories.from_vertebrata().load(7742)
        assert len(tax) == 100670
        assert tax.roots == [Taxon(7742, "Vertebrata", None, None, None, set())]
        assert len(tax.roots[0].descendents) == 100669
        assert tax[7742] is not None
        assert tax[7742].scientific_name == "Vertebrata"
        assert tax[7742].parent is None
        assert tax[117571].id == 117571
        assert tax[117571].scientific_name == "Euteleostomi"
        assert tax[10116].scientific_name == "Rattus norvegicus"
        assert 117571 in tax
        assert [c.id for c in tax[117571].children] == [7898, 8287]
        with pytest.raises(KeyError):
            assert tax[3343463643446436347457475]
        assert tax.get(3343463643446436347457475) is None
        assert tax.get(117571).id == 117571
        assert 117571 in tax
        assert 13745754745745 not in tax

    def test_empty(self):
        tax = Taxonomy({}, {})
        assert len(tax) == 0
        assert tax.roots == []

    def test_root_leaf(self):
        taxon = Taxon(1, "abc", None, None, None, set())
        tax = Taxonomy.from_list([taxon])
        assert len(tax) == 1
        assert tax.roots == [taxon]
        assert tax.leaves == [taxon]

    def test_double(self):
        a = _Taxon(1, "a", None, None, None, set())
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
        a = _Taxon(10, "z", None, None, None, set())
        b = _Taxon(2, "a", None, None, a, set())
        c = _Taxon(4, "b", None, None, a, set())
        assert b < c, f"{b} vs {c}"
        assert b < c < a, f"{a} vs {b} vs {c}"

    """
    def test_real(self):
        path = MandosResources.path("7742.snappy")
        tax = Taxonomy.from_path(path)
        assert len(tax) == 100670
        tax = tax.subtree(117571)
        # number from https://www.uniprot.org/taxonomy/117571
        assert len(tax) == 97993

    def test_real_by_name(self):
        path = MandosResources.path("7742.snappy")
        tax = Taxonomy.from_path(path)
        eu = tax.subtrees_by_name("Sarcopterygii")
        assert len(eu) == 53827
    """


if __name__ == "__main__":
    pytest.main()
