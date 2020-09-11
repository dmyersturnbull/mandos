from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence, Set, Union

import pandas as pd

logger = logging.getLogger(__package__)


@dataclass(order=True)
class Taxon:
    id: int
    name: str
    parent: Optional[Taxon]
    children: Set[Taxon]

    def __hash__(self):
        return hash(self.id)


class Taxonomy:
    """
    A taxonomic tree of organisms from UniProt.
    Elements in the tree can be looked up by name or ID using ``__getitem__`` and ``get``.
    """

    def __init__(self, by_id: Mapping[int, Taxon], by_name: Mapping[str, Taxon]):
        self._by_id = by_id
        self._by_name = by_name

    @classmethod
    def from_list(cls, taxa: Sequence[Taxon]) -> Taxonomy:
        return Taxonomy({x.id: x for x in taxa}, {x.name: x for x in taxa})

    @classmethod
    def from_df(cls, df: pd.DataFrame) -> Taxonomy:
        """
        Reads from a DataFrame from a CSV file provided by a UniProt download.
        Strips any entries with missing or empty-string scientific names.

        Args:
            df: A dataframe with columns (at least) "Taxon", "Scientific name", and "Parent" (case-insensitive)

        Returns:
            The corresponding taxonomic tree
        """
        df.columns = [c.lower() for c in df.columns]
        df = df[["taxon", "scientific name", "parent"]]
        df.columns = ["id", "name", "parent"]
        tax = Taxonomy({}, {})
        # just build up a tree, sticking the elements in by_id
        tax._by_id = {}
        for row in df.itertuples():
            child = tax._by_id.setdefault(row.id, Taxon(row.id, row.name, None, set()))
            parent = tax._by_id.setdefault(row.parent, Taxon(row.parent, "", None, set()))
            child.name, child.parent = row.name, parent
            parent.children.add(child)
        bad = [t for t in tax._by_id.values() if t.name == ""]
        if len(bad) > 0:
            logger.error(f"Removing taxa with missing or empty names: {bad}.")
        # completely remove the taxa with missing names
        tax._by_id = {k: v for k, v in tax._by_id.items() if v.name != ""}
        # build the name dict
        # use lowercase and trim for lookup (but not value)
        tax._by_name = {t.name.strip().lower(): t for t in tax._by_id.values()}
        return tax

    @property
    def taxa(self) -> Sequence[Taxon]:
        return list(self._by_id.values())

    @property
    def roots(self) -> Sequence[Taxon]:
        return [k for k in self.taxa if k.parent is None]

    @property
    def leaves(self) -> Sequence[Taxon]:
        return [k for k in self.taxa if len(k.children) == 0]

    def get(self, item: Union[int, str]) -> Optional[Taxon]:
        """
        Corresponds to ``dict.get``.

        Args:
            item: The scientific name or UniProt ID

        Returns:
            The taxon, or None if it was not found
        """
        if isinstance(item, int):
            return self._by_id.get(item)
        elif isinstance(item, str):
            return self._by_name.get(item.strip().lower())
        else:
            raise TypeError(f"Type {type(item)} of {item} not applicable")

    def __getitem__(self, item: Union[int, str]) -> Taxon:
        """
        Corresponds to ``dict[_]``.

        Args:
            item: The scientific name or UniProt ID

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
        return self.get(item) is not None

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({len(self._by_id)} @ {hex(id(self))})"

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({len(self._by_id)} @ {hex(id(self))})"
