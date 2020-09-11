from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Set

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit
from mandos.taxonomy import Taxon, Taxonomy
from mandos.utils import Utils

logger = logging.getLogger("mandos")


@dataclass(order=True)
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


@dataclass(frozen=True, order=True)
class AtcHit(AbstractHit):
    atc: AtcCode
    src_id: int

    @property
    def predicate(self) -> str:
        return "has ATC code"


class AtcSearch:
    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def find(self, compound: str) -> Sequence[AtcHit]:
        c = Utils.get_compound(compound)
        results = Chembl.atc.filter(molecule_chembl_id=c.chid)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(compound, result))
        return hits
