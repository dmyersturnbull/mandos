from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, ChemblCompound, Search
from mandos.model.atc_codes import AtcCode

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class AtcHit(AbstractHit):
    """
    An ATC code found for a compound.
    """

    level: int

    @property
    def predicate(self) -> str:
        return f"has ATC L-{self.level} code"


class AtcSearch(Search[AtcHit]):
    """"""

    def find(self, lookup: str) -> Sequence[AtcHit]:
        """

        Args:
            lookup:

        Returns:

        """
        # 'atc_classifications': ['S01HA01', 'N01BC01', 'R02AD03', 'S02DA02']
        # 'indication_class': 'Anesthetic (topical)'
        ch = self.get_compound_dot_dict(lookup)
        compound = self.compound_dot_dict_to_obj(ch)
        hits = []
        if "atc_classifications" in ch:
            for atc in ch["atc_classifications"]:
                hits.extend(self.process(lookup, compound, atc))
        return hits

    def process(self, lookup: str, compound: ChemblCompound, atc: str) -> Sequence[AtcHit]:
        """

        Args:
            lookup:
            compound:
            atc:

        Returns:

        """
        dots = NestedDotDict(self.api.atc_class.get(atc))
        # 'level1': 'N', 'level1_description': 'NERVOUS SYSTEM', 'level2': 'N05', ...
        code = None
        for level in [1, 2, 3, 4]:
            if f"level{level}" not in dots:
                break
            code = AtcCode(dots[f"level{level}"], dots[f"level{level}_description"], level, code)
        hit1 = AtcHit(
            None,
            compound.chid,
            compound.inchikey,
            lookup,
            compound.name,
            object_id=code.record,
            object_name=code.description,
            level=code.level,
        )
        hit2 = AtcHit(
            None,
            compound.chid,
            compound.inchikey,
            lookup,
            compound.name,
            object_id=code.parent.record,
            object_name=code.parent.description,
            level=code.parent.level,
        )
        return [hit1, hit2]


__all__ = ["AtcHit", "AtcSearch"]
