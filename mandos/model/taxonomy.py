from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import (FrozenSet, Iterable, List, Mapping, Optional, Sequence,
                    Set, Union)

import pandas as pd
from typeddfs import TypedDfs

from mandos import logger

TaxonomyDf = (
    TypedDfs.typed("TaxonomyDf")
    .require("taxon")
    .require("parent")
    .require("scientific_name")
    .reserve("common_name")
).build()


@total_ordering
@dataclass()
class Taxon:
    """ """

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


TaxaIdsAndNames = Union[int, str, Taxon, Iterable[Union[int, str, Taxon]]]
TaxonIdOrName = Union[int, str, Taxon]


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

    def __init__(self, by_id: Mapping[int, Taxon], by_name: Mapping[str, FrozenSet[Taxon]]):
        """

        Args:
            by_id:
        """
        # constructor provided for consistency with the members
        self._by_id = dict(by_id)
        self._by_name = dict(by_name)
        # this probably isn't actually possible
        if len(self) == 0:
            logger.warning(f"{self} contains 0 taxa")

    @classmethod
    def from_trees(cls, taxonomies: Sequence[Taxonomy]) -> Taxonomy:
        # we need to rewrite the ancestors, which from_df already does
        # so we'll just use that
        dfs = [tree.to_df() for tree in taxonomies]
        df = TaxonomyDf(pd.concat(dfs, ignore_index=True))
        df = df.drop_duplicates().sort_values("taxon")
        return Taxonomy.from_df(df)

    @classmethod
    def from_list(cls, taxa: Sequence[Taxon]) -> Taxonomy:
        by_id = {x.id: x for x in taxa}
        by_name = cls._build_by_name(by_id.values())
        tax = Taxonomy(by_id, by_name)
        # catch duplicate values
        if len(tax._by_id) != len(taxa):
            raise AssertionError(f"{len(tax._by_id)} != {len(taxa)}")
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
        by_name = cls._build_by_name(tax.values())
        return Taxonomy(tax, by_name)

    def to_df(self) -> TaxonomyDf:
        return TaxonomyDf(
            [
                pd.Series(dict(taxon=taxon.id, scientific_name=taxon.name, parent=taxon.parent.id))
                for taxon in self.taxa
            ]
        )

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
        return [k for k in self.taxa if len(k.children) == 0]

    def exclude_subtree(self, item: Union[int, Taxon]) -> Taxonomy:
        descendents = self.get_by_id_or_name(item)
        for i in set(descendents):
            descendents += i.descendents
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def exclude_subtrees_by_ids_or_names(self, items: TaxaIdsAndNames) -> Taxonomy:
        if isinstance(items, (int, str, Taxon)):
            items = [items]
        bad_taxa = self.subtrees_by_ids_or_names(items).taxa
        by_id = {i: t for i, t in self._by_id.items() if i not in bad_taxa}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def subtree(self, item: int) -> Taxonomy:
        item = self[item]
        descendents = {item, *item.descendents}
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def subtrees_by_ids_or_names(self, items: TaxaIdsAndNames) -> Taxonomy:
        if isinstance(items, (int, str, Taxon)):
            items = [items]
        descendents: Set[Taxon] = set()
        for item in items:
            for taxon in self.get_by_id_or_name(item):
                descendents += {taxon, *taxon.descendents}
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def subtrees_by_name(self, item: str) -> Taxonomy:
        """
        Returns the taxonomy that rooted at each of the taxa with the specified scientific name.
        """
        return self.subtrees_by_names(item)

    def subtrees_by_names(self, items: Iterable[str]) -> Taxonomy:
        descendents: Set[Taxon] = set()
        for item in items:
            for taxon in self._by_name.get(item, []):
                descendents.update({taxon, *taxon.descendents})
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def req_one_by_name(self, item: str) -> Taxon:
        """
        Gets a single taxon by its name.
        If there are multiple, returns the first (lowest ID).
        Raises an error if there are no matches.
        """
        one = self.get_one_by_name(item)
        if one is None:
            raise LookupError(f"No taxa for {item}")
        return one

    def req_only_by_name(self, item: str) -> Taxon:
        """
        Gets a single taxon by its name.
        Raises an error if there are multiple matches for the name, or if there are no matches.
        """
        taxa = self.get_by_name(item)
        ids = ",".join([str(t.id) for t in taxa])
        if len(taxa) > 1:
            raise ValueError(f"Got multiple results for {item}: {ids}")
        elif len(taxa) == 0:
            raise LookupError(f"No taxa for {item}")
        return next(iter(taxa))

    def get_one_by_name(self, item: str) -> Optional[Taxon]:
        """
        Gets a single taxon by its name.
        If there are multiple, returns the first (lowest ID).
        If there are none, returns ``None``.
        """
        taxa = self.get_by_name(item)
        ids = ",".join([str(t.id) for t in taxa])
        if len(taxa) > 1:
            logger.warning(f"Got multiple results for {item}: {ids}")
        elif len(taxa) == 0:
            return None
        return next(iter(taxa))

    def get_by_name(self, item: str) -> FrozenSet[Taxon]:
        """
        Gets all taxa that match a scientific name.
        """
        if isinstance(item, Taxon):
            item = item.name
        return self._by_name.get(item, frozenset(set()))

    def get_all_by_id_or_name(self, items: Iterable[Union[int, str, Taxon]]) -> FrozenSet[Taxon]:
        """
        Gets all taxa that match any number of IDs or names.
        """
        matching = []
        for item in items:
            matching += self.get_by_id_or_name(item)
        # finally de-duplicates (making this fn useful)
        return frozenset(matching)

    def get_by_id_or_name(self, item: Union[int, str, Taxon]) -> FrozenSet[Taxon]:
        """
        Gets all taxa that match an ID or name.
        """
        if isinstance(item, Taxon):
            item = item.id
        if isinstance(item, int):
            taxon = self._by_id.get(item)
            return frozenset([]) if taxon is None else frozenset([taxon])
        elif isinstance(item, str):
            return self._by_name.get(item, frozenset(set()))
        else:
            raise TypeError(f"Unknown type {type(item)} of {item}")

    def req(self, item: int) -> Taxon:
        """
        Gets a single taxon by its ID.
        Raises an error if it is not found.
        """
        if isinstance(item, Taxon):
            item = item.id
        return self[item]

    def get(self, item: Union[int, Taxon]) -> Optional[Taxon]:
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

    def contains(self, item: Union[Taxon, int, str]):
        return self.get(item) is not None

    def n_taxa(self) -> int:
        return len(self._by_id)

    def __contains__(self, item: Union[Taxon, int, str]):
        return self.get(item) is not None

    def __len__(self) -> int:
        return len(self._by_id)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        roots = ", ".join(r.name for r in self.roots)
        return f"{self.__class__.__name__}(n={len(self._by_id)} (roots={roots}) @ {hex(id(self))})"

    @classmethod
    def _build_by_name(cls, tax: Iterable[Taxon]) -> Mapping[str, FrozenSet[Taxon]]:
        by_name = defaultdict(set)
        for t in tax:
            by_name[t.name].add(t)
        # NOTE: lower-casing the keys for lookup
        return {k.lower(): frozenset(v) for k, v in by_name.items()}


__all__ = ["Taxon", "Taxonomy", "TaxonomyDf"]
