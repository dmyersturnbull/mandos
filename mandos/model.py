from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Dict, Generator, Optional, Sequence, Set, Union

import pandas as pd
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.utils import NestedDotDict

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
    def __init__(self, by_id: Dict[int, Taxon], by_name: Dict[str, Taxon]):
        self._by_id = by_id
        self._by_name = by_name

    @classmethod
    def from_list(cls, taxa: Sequence[Taxon]) -> Taxonomy:
        return Taxonomy({x.id: x for x in taxa}, {x.name: x for x in taxa})

    @classmethod
    def from_df(cls, df: pd.DataFrame) -> Taxonomy:
        df.columns = [c.lower() for c in df.columns]
        df = df[["taxon", "scientific name", "parent"]]
        df.columns = ["id", "name", "parent"]
        tax = Taxonomy({}, {})
        tax._by_id = {}
        for row in df.itertuples():
            # noinspection PyTypeChecker
            child = tax._by_id.setdefault(row.id, Taxon(row.id, row.name, None, set()))
            # noinspection PyTypeChecker
            parent = tax._by_id.setdefault(row.parent, Taxon(row.parent, None, None, set()))
            child.name, child.parent = row.name, parent
            parent.children.add(child)
        bad = [t for t in tax._by_id.values() if t.name is None]
        if len(bad) > 0:
            logger.error(f"Taxa are missing names: {bad}")
        tax._by_id = {k: v for k, v in tax._by_id.items() if v.name is not None}
        tax._by_name = {
            t.name.strip().lower(): t for t in tax._by_id.values() if t.name is not None
        }
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
        if isinstance(item, int):
            return self._by_id.get(item)
        elif isinstance(item, str):
            return self._by_name.get(item.strip().lower())
        else:
            raise TypeError(f"Type {type(item)} of {item} not applicable")

    def __getitem__(self, item: Union[int, str]) -> Taxon:
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


class TargetType(enum.Enum):
    single_protein = enum.auto()
    protein_family = enum.auto()
    protein_complex = enum.auto()
    protein_complex_group = enum.auto()
    selectivity_group = enum.auto()

    @property
    def parent(self) -> Optional[TargetType]:
        if self is TargetType.single_protein:
            return TargetType.protein_family


@dataclass(order=True)
class Target:
    id: int
    name: str
    type: TargetType

    @property
    def chembl(self) -> str:
        return "CHEMBL" + str(self.id)

    def links(self) -> Sequence[Target]:
        relations = Chembl.target_relation.filter(target_chembl_id=self.chembl)
        links = []
        for superset in [r for r in relations if r["relationship"] == "SUPERSET OF"]:
            linked_target = self.find(superset["related_target_chembl_id"])
            links.append(linked_target)
        return links

    def traverse(self, permitting: Set[TargetType]) -> Set[Target]:
        results = set()
        self._traverse(permitting, results)
        return results

    def _traverse(self, permitting: Set[TargetType], results: Set[Target]) -> Set[Target]:
        for linked in self._traverse(permitting, results):
            if linked.type in permitting:
                results.add(linked)
        results.add(self)
        return results

    @classmethod
    def find(cls, chembl: str) -> Target:
        targets = Chembl.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
        target = NestedDotDict(targets[0])
        return Target(
            id=int(target["target_chembl_id"].replace("CHEMBL", "")),
            name=target["pref_target_name"],
            type=TargetType[target["target_type"].replace(" ", "_")],
        )
