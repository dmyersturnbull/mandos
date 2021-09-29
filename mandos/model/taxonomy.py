from __future__ import annotations

import enum
from collections import defaultdict
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import (
    Collection,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Union,
    Dict,
)

import pandas as pd
from pocketutils.core.exceptions import DataIntegrityError, LookupFailedError, XTypeError
from typeddfs import TypedDfs

from mandos.model import MultipleMatchesError
from mandos.model.utils import CleverEnum
from mandos.model.utils.setup import logger


class KnownTaxa:
    """
    Taxa whose IDs are used in the code.
    """

    biota = 131567  # 2 million nodes
    eukaryota = 2759  # 1.5 million nodes
    metazoa = 33208  # 1 million
    vertebrata = 7742  # 100,000 nodes
    euteleostomi = 117571  # 100,000 nodes
    human = 9606
    rat = 10116
    mouse = 10090


class NameType(CleverEnum):
    """
    Scientific name, common name, or mnemonic.
    """

    scientific = enum.auto()
    common = enum.auto()
    mnemonic = enum.auto()


TaxonomyDf = (
    TypedDfs.typed("TaxonomyDf")
    .require("taxon", "parent", dtype=int)
    .require("mnemonic", "scientific_name", "common_name", dtype=str)
    .strict()
    .secure()
).build()


@total_ordering
@dataclass()
class Taxon:
    """ """

    # we can't use frozen=True because we have both parents and children
    # instead, just use properties
    __id: int
    __scientific_name: str
    __common_name: Optional[str]
    __mnemonic: Optional[str]
    __parent: Optional[Taxon]
    __children: Set[Taxon]

    @property
    def id(self) -> int:
        """
        Returns the UniProt ID of this taxon.
        """
        return self.__id

    @property
    def scientific_name(self) -> str:
        """
        Returns the scientific name of this taxon.
        """
        return self.__scientific_name

    @property
    def common_name(self) -> Optional[str]:
        """
        Returns the common name of this taxon, or None if it has none.
        """
        return self.__common_name

    @property
    def mnemonic(self) -> Optional[str]:
        """
        Returns the mnemonic of this taxon, or None if it has none.
        Only ~16 taxa have mnemonics as of 2021-08.
        For example: "BOVIN" `<https://www.uniprot.org/taxonomy/9913>`_.
        """
        return self.__mnemonic

    @property
    def keys(self) -> FrozenSet[Union[int, str]]:
        """
        Returns the IDs and names that can be used to find this taxon.
        Specifically, includes the ID (int), scientific name (str),
        common name (str; if any), and mnemonic (str; if any).
        """
        keys = {self.id, self.scientific_name, self.common_name, self.mnemonic}
        return frozenset({s for s in keys if s is not None})

    @property
    def as_series(self) -> pd.Series:
        return pd.Series(
            dict(
                taxon=self.id,
                scientific_name=self.scientific_name,
                common_name=self.common_name,
                mnemonic=self.mnemonic,
                parent=self.parent.id,
            )
        )

    @property
    def parent(self) -> Taxon:
        """
        Returns the parent of this taxon.
        """
        return self.__parent

    @property
    def children(self) -> Set[Taxon]:
        """
        Returns the immediate descendents of this taxon.
        """
        return set(self.__children)

    @property
    def ancestors(self) -> Sequence[Taxon]:
        """
        Returns all taxa that are ancestors of, or identical to, this taxon.
        """
        lst = []
        self._ancestors(lst)
        return lst

    @property
    def descendents(self) -> Sequence[Taxon]:
        """
        Returns all taxa that are descendents of, or identical to, this taxon.
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
        parent = self.parent.id if self.parent else "none"
        return f"{self.__class__.__name__}({self.id}: {self.scientific_name} (parent={parent}))"

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

    def set_names(self, scientific: str, common: Optional[str], mnemonic: Optional[str]):
        self.__scientific_name = scientific
        self.__common_name = common
        self.__mnemonic = mnemonic

    def set_parent(self, parent: _Taxon):
        self.__parent = parent

    def add_child(self, child: _Taxon):
        self.__children.add(child)

    # weirdly these are required again -- probably an issue with dataclass

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}: {self.scientific_name} (parent={self.parent.id if self.parent else 'none'}))"

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
    def from_trees(cls, taxonomies: Collection[Taxonomy]) -> Taxonomy:
        # we need to rewrite the ancestors, which from_df already does
        # so we'll just use that
        dfs = [tree.to_df() for tree in taxonomies]
        if len(dfs) == 0:
            df = TaxonomyDf.new_df()
        else:
            df = TaxonomyDf.of(pd.concat(dfs, ignore_index=True))
        df = df.drop_duplicates().sort_values("taxon")
        return Taxonomy.from_df(df)

    @classmethod
    def from_list(cls, taxa: Collection[Taxon]) -> Taxonomy:
        by_id = {x.id: x for x in taxa}
        by_name = cls._build_by_name(by_id.values())
        tax = Taxonomy(by_id, by_name)
        # catch duplicate values
        if len(tax._by_id) != len(taxa):
            raise DataIntegrityError(f"{len(tax._by_id)} != {len(taxa)}")
        return tax

    @classmethod
    def from_path(cls, path: Path) -> Taxonomy:
        """
        Reads from a DataFrame file.
        """
        df = TaxonomyDf.read_file(path)
        return cls.from_df(df)

    @classmethod
    def from_df(cls, df: TaxonomyDf) -> Taxonomy:
        """
        Reads from a DataFrame from a file provided by a UniProt download.
        Strips any entries with missing or empty-string scientific names.

        Args:
            df: A TaxonomyDf DataFrame

        Returns:
            The corresponding taxonomic tree
        """
        # just build up a tree, sticking the elements in by_id
        tax: Dict[int, _Taxon] = {}
        for row in df.itertuples():
            _new_child = _Taxon(
                row.taxon, row.scientific_name, row.common_name, row.mnemonic, None, set()
            )
            child = tax.setdefault(row.taxon, _new_child)
            child.set_names(row.scientific_name, row.common_name, row.mnemonic)
            if row.parent != 0:
                _new_parent = _Taxon(row.parent, "", None, None, None, set())
                parent = tax.setdefault(row.parent, _new_parent)
                child.set_parent(parent)
                parent.add_child(child)
        bad = [t for t in tax.values() if t.scientific_name.strip() == ""]
        if len(bad) > 0:
            raise DataIntegrityError(
                f"{len(bad)} taxa with missing or empty scientific names: {bad}."
            )
        for v in tax.values():
            v.__class__ = Taxon
        by_name = cls._build_by_name(tax.values())
        return Taxonomy(tax, by_name)

    def to_df(self) -> TaxonomyDf:
        return TaxonomyDf.convert(pd.DataFrame([taxon.as_series for taxon in self.taxa]))

    @property
    def taxa(self) -> Sequence[Taxon]:
        """
        Returns all taxa in the tree.
        """
        return list(self._by_id.values())

    @property
    def roots(self) -> Sequence[Taxon]:
        """
        Returns the roots of the tree (at least 1).
        """
        return [k for k in self.taxa if k.parent is None or k.parent not in self]

    @property
    def leaves(self) -> Sequence[Taxon]:
        """
        Returns the leaves (typically species or sub-species) of the tree.
        """
        return [k for k in self.taxa if len(k.children) == 0]

    def exclude_subtree(self, item: Union[int, Taxon]) -> Taxonomy:
        """
        Returns a new tree that excludes a single specified taxon and its descendents.
        """
        descendents = self.get_by_id_or_name(item)
        for i in set(descendents):
            descendents += i.descendents
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def exclude_subtrees_by_ids_or_names(self, items: TaxaIdsAndNames) -> Taxonomy:
        """
        Returns a tree tree that excludes taxa that are descendents of the specified taxa.
        If a name is used in multiple taxa, all of those will be used to exclude.

        Arguments:
            items: A scientific name, common name, or mnemonic; or a sequence of them
        """
        if isinstance(items, (int, str, Taxon)):
            items = [items]
        bad_taxa = self.subtrees_by_ids_or_names(items).taxa
        by_id = {i: t for i, t in self._by_id.items() if i not in bad_taxa}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def subtree(self, item: int) -> Taxonomy:
        """
        Returns the tree that is rooted at a single taxon (by ID).
        """
        item = self[item]
        descendents = {item, *item.descendents}
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def subtrees_by_ids_or_names(self, items: TaxaIdsAndNames) -> Taxonomy:
        """
        Returns the tree that is rooted at the specified taxa (by name or ID).
        The tree will have *at most* ``len(items)`` roots.

        Arguments:
            items: A scientific name, common name, or mnemonic; or a sequence of them
        """
        if isinstance(items, (int, str, Taxon)):
            items = [items]
        descendents: Set[Taxon] = set()
        for item in items:
            for taxon in self.get_by_id_or_name(item):
                descendents.update({taxon, *taxon.descendents})
        by_id = {d.id: d for d in descendents}
        by_name = self.__class__._build_by_name(by_id.values())
        return Taxonomy(by_id, by_name)

    def subtrees_by_name(self, item: str) -> Taxonomy:
        """
        Returns the tree rooted at the taxa with the specified scientific name.

        Arguments:
            item: A scientific name, common name, or mnemonic
        """
        return self.subtrees_by_names(item)

    def subtrees_by_names(self, items: Iterable[str]) -> Taxonomy:
        """
        Returns the tree rooted at the specified taxa (by scientific name).

        Arguments:
            items: A sequence of scientific name, common name, and/or mnemonics
        """
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

        Arguments:
            item: A scientific name, common name, or mnemonic

        Raises:
            LookupError: If not found
            MultipleMatchesError: If multiple are found
        """
        one = self.get_one_by_name(item)
        if one is None:
            raise LookupFailedError(f"No taxa for {item}")
        return one

    def req_only_by_name(self, item: str) -> Taxon:
        """
        Gets a single taxon by its name.
        Raises an error if there are multiple matches for the name, or if there are no matches.

        Arguments:
            item: A scientific name, common name, or mnemonic

        Raises:
            LookupError: If not found
            MultipleMatchesError: If multiple are found
        """
        taxa = self.get_by_name(item)
        ids = ",".join([str(t.id) for t in taxa])
        if len(taxa) > 1:
            raise MultipleMatchesError(f"Got multiple results for {item}: {ids}")
        elif len(taxa) == 0:
            raise LookupFailedError(f"No taxa for {item}")
        return next(iter(taxa))

    def get_one_by_name(self, item: str) -> Optional[Taxon]:
        """
        Gets a single taxon by its name.
        If there are multiple, returns the first (lowest ID).
        If there are none, returns ``None``.
        Logs at warning level if multiple matched.

        Arguments:
            item: A scientific name, common name, or mnemonic
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
            item = item.scientific_name
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
            raise XTypeError(f"Unknown type {type(item)} of {item}")

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
        elif isinstance(item, str):
            return self._by_id.get(item)
        else:
            raise XTypeError(f"Type {type(item)} of {item} not applicable")

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
            raise LookupFailedError(f"{item} not found in {self}")
        return got

    def contains(self, item: Union[Taxon, int, str]):
        return self.get(item) is not None

    def n_taxa(self) -> int:
        return len(self._by_id)

    def __contains__(self, item: Union[Taxon, int, str]):
        if isinstance(item, str):
            return self._by_name.get(item) is not None
        return self.get(item) is not None

    def __len__(self) -> int:
        return len(self._by_id)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        roots = ", ".join(r.scientific_name for r in self.roots)
        return f"{self.__class__.__name__}(n={len(self._by_id)} (roots={roots}) @ {hex(id(self))})"

    @classmethod
    def _build_by_name(cls, tax: Iterable[Taxon]) -> Mapping[str, FrozenSet[Taxon]]:
        by_name = defaultdict(set)
        # put these in the right order
        # so that we favor mnemonic, then scientific name, then common name
        for t in tax:
            if t.mnemonic is not None:
                by_name[t.mnemonic].add(t)
        for t in tax:
            by_name[t.scientific_name].add(t)
        for t in tax:
            if t.common_name is not None:
                by_name[t.common_name].add(t)
        # NOTE: lower-casing the keys for lookup
        return {k.lower(): frozenset(v) for k, v in by_name.items()}


__all__ = ["Taxon", "Taxonomy", "TaxonomyDf", "KnownTaxa"]
