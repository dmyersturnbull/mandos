from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Set

import pandas as pd
from typeddfs import TypedDfs

logger = logging.getLogger(__package__)

TaxonomyDf = (
    TypedDfs.typed("TaxonomyDf").require("taxon").require("parent").require("scientific_name")
).build()


@total_ordering
@dataclass()
class Taxon:
    """"""

    # we can't use frozen=True because we have both parents and children
    # instead, just use properties
    __id: int
    __name: str
    __parent: Optional[Taxon]
    __children: Set[Taxon]

    @property
    def id(self) -> int:
        """

        Returns:

        """
        return self.__id

    @property
    def name(self) -> str:
        """

        Returns:

        """
        return self.__name

    @property
    def parent(self) -> Taxon:
        """

        Returns:

        """
        return self.__parent

    @property
    def children(self) -> Set[Taxon]:
        """

        Returns:

        """
        return set(self.__children)

    @property
    def ancestors(self) -> Sequence[Taxon]:
        """

        Returns:

        """
        lst = []
        self._ancestors(lst)
        return lst

    @property
    def descendents(self) -> Sequence[Taxon]:
        """

        Returns:

        """
        lst = []
        self._descendents(lst)
        return lst

    def _ancestors(self, values: List[Taxon]) -> None:
        values.append(self.parent)
        self.parent._ancestors(values)

    def _descendents(self, values: List[Taxon]) -> None:
        values.extend(self.children)
        for child in self.children:
            child._descendents(values)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}: {self.name} (parent={self.parent.id if self.parent else 'none'}))"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id


@dataclass()
class _Taxon(Taxon):
    """
    An internal, modifiable taxon for building the tree.
    """

    def set_name(self, name: str):
        self.__name = name

    def set_parent(self, parent: _Taxon):
        self.__parent = parent

    def add_child(self, child: _Taxon):
        self.__children.add(child)

    # weirdly these are required again -- probably an issue with dataclass

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}: {self.name} (parent={self.parent.id if self.parent else 'none'}))"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id


class Taxonomy:
    """
    A taxonomic tree of organisms from UniProt.
    Elements in the tree can be looked up by name or ID using ``__getitem__`` and ``get``.
    """

    def __init__(self, by_id: Mapping[int, Taxon]):
        """

        Args:
            by_id:
        """
        # constructor provided for consistency with the members
        self._by_id = dict(by_id)

    @classmethod
    def from_list(cls, taxa: Sequence[Taxon]) -> Taxonomy:
        tax = Taxonomy({x.id: x for x in taxa})
        # catch duplicate values
        assert len(tax._by_id) == len(taxa), f"{len(tax._by_id)} != {len(taxa)}"
        return tax

    @classmethod
    def from_path(cls, path: Path) -> Taxonomy:
        df = pd.read_csv(path, sep="\t", header=0)
        return cls.from_df(df)

    @classmethod
    def from_df(cls, df: TaxonomyDf) -> Taxonomy:
        """
        Reads from a DataFrame from a CSV file provided by a UniProt download.
        Strips any entries with missing or empty-string scientific names.

        Args:
            df: A dataframe with columns (at least) "taxon", "scientific_name", and "parent"

        Returns:
            The corresponding taxonomic tree
        """
        df["taxon"] = df["taxon"].astype(int)
        # TODO fillna(0) should not be needed
        df["parent"] = df["parent"].fillna(0).astype(int)
        # just build up a tree, sticking the elements in by_id
        tax = {}
        for row in df.itertuples():
            child = tax.setdefault(row.taxon, _Taxon(row.taxon, row.scientific_name, None, set()))
            child.set_name(row.scientific_name)
            if row.parent != 0:
                parent = tax.setdefault(row.parent, _Taxon(row.parent, "", None, set()))
                child.set_parent(parent)
                parent.add_child(child)
        bad = [t for t in tax.values() if t.name.strip() == ""]
        if len(bad) > 0:
            raise ValueError(f"There are taxa with missing or empty names: {bad}.")
        for v in tax.values():
            v.__class__ = Taxon
        return Taxonomy(tax)

    @property
    def taxa(self) -> Sequence[Taxon]:
        """

        Returns:

        """
        return list(self._by_id.values())

    @property
    def roots(self) -> Sequence[Taxon]:
        """

        Returns:

        """
        return [k for k in self.taxa if k.parent is None or k.parent not in self]

    @property
    def leaves(self) -> Sequence[Taxon]:
        """

        Returns:

        """
        return [k for k in self.taxa if len(k.children) == 0]

    def subtree(self, item: int) -> Taxonomy:
        """

        Args:
            item:

        Returns:

        """
        item = self[item]
        descendents = {item, *item.descendents}
        return Taxonomy({d.id: d for d in descendents})

    def req(self, item: int) -> Taxon:
        if isinstance(item, Taxon):
            item = item.id
        return self[item]

    def get(self, item: int) -> Optional[Taxon]:
        """
        Corresponds to ``dict.get``.

        Args:
            item: The scientific name or UniProt ID

        Returns:
            The taxon, or None if it was not found
        """
        if isinstance(item, Taxon):
            item = item.id
        if isinstance(item, int):
            return self._by_id.get(item)
        else:
            raise TypeError(f"Type {type(item)} of {item} not applicable")

    def __getitem__(self, item: int) -> Taxon:
        """
        Corresponds to ``dict[_]``.

        Args:
            item: The UniProt ID

        Returns:
            The taxon

        Raises:
            KeyError: If the taxon was not found
        """
        got = self.get(item)
        if got is None:
            raise KeyError(f"{item} not found in {self}")
        return got

    def __contains__(self, item):
        """

        Args:
            item:

        Returns:

        """
        return self.get(item) is not None

    def __len__(self) -> int:
        """

        Returns:

        """
        return len(self._by_id)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        roots = ", ".join(r.name for r in self.roots)
        return f"{self.__class__.__name__}(n={len(self._by_id)} (roots={roots}) @ {hex(id(self))})"


__all__ = ["Taxon", "Taxonomy"]
