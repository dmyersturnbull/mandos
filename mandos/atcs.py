from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional, Sequence, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, Search
from mandos.model.utils import ChemblCompound, Utils

logger = logging.getLogger("mandos")


@total_ordering
@dataclass()
class AtcCode:
    record: str
    description: str
    level: int
    parent: AtcCode
    children: Set[AtcCode]

    def traverse_to(self, level: int) -> Optional[AtcCode]:
        if level < 1:
            raise ValueError(f"Level {level} < 1")
        if self.level == level:
            return self
        elif self.level < level:
            return self.parent.traverse_to(level)
        else:
            return None

    def __hash__(self):
        return hash(self.record)

    def __eq__(self, other):
        if not isinstance(other, AtcCode):
            raise TypeError(f"{type(other)} is not an AtcCode")
        return self.record == other.record

    def __lt__(self, other):
        if not isinstance(other, AtcCode):
            raise TypeError(f"{type(other)} is not an AtcCode")
        return self.record < other.record


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class AtcHit(AbstractHit):
    atc: AtcCode
    src_id: int

    @property
    def predicate(self) -> str:
        return "has ATC code"


class AtcSearch(Search[AtcHit]):
    def find(self, lookup: str) -> Sequence[AtcHit]:
        # 'atc_classifications': ['S01HA01', 'N01BC01', 'R02AD03', 'S02DA02']
        # 'indication_class': 'Anesthetic (topical)'
        ch = Utils.get_compound_dot_dict(lookup)
        # TODO duplicated
        chid = ch["molecule_chembl_id"]
        inchikey = ch["molecule_structures"]["standard_inchi_key"]
        name = ch["pref_name"]
        compound = ChemblCompound(chid, inchikey, name)
        hits = []
        for atc in ch["atc_classifications"]:
            hits.extend(self.process(lookup, compound, atc))
        return hits

    def process(self, lookup: str, compound: ChemblCompound, atc: str) -> Sequence[AtcHit]:
        # TODO get from file
        return []
