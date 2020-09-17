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

    atc_level_3: AtcCode
    atc_level_4: AtcCode

    @property
    def predicate(self) -> str:
        return "has ATC code"


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
                hits.append(self.process(lookup, compound, atc))
        return hits

    def process(self, lookup: str, compound: ChemblCompound, atc: str) -> AtcHit:
        """

        Args:
            lookup:
            compound:
            atc:

        Returns:

        """
        dots = NestedDotDict(self.api.atc_class.get(atc))
        code = None
        for level in [1, 2, 3, 4]:
            if f"level{level}" not in dots:
                break
            code = AtcCode(dots[f"level{level}"], dots[f"level{level}_description"], level, code)
        hit = AtcHit(
            None, compound.chid, compound.inchikey, lookup, compound.name, code.parent, code
        )
        # 'level1': 'N', 'level1_description': 'NERVOUS SYSTEM', 'level2': 'N05', ...
        return hit
