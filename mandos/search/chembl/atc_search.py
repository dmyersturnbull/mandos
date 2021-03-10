from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_support.chembl_utils import ChemblUtils
from mandos.model.chembl_support import ChemblCompound
from mandos.search.chembl import ChemblSearch, ChemblHit

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True)
class AtcHit(ChemblHit):
    """
    An ATC code found for a compound.
    """

    level: int

    @property
    def predicate(self) -> str:
        return f"has ATC L-{self.level} code"


class AtcSearch(ChemblSearch[AtcHit]):
    """"""

    def find(self, lookup: str) -> Sequence[AtcHit]:
        """

        Args:
            lookup:

        Returns:

        """
        # 'atc_classifications': ['S01HA01', 'N01BC01', 'R02AD03', 'S02DA02']
        # 'indication_class': 'Anesthetic (topical)'
        ch = ChemblUtils(self.api).get_compound_dot_dict(lookup)
        compound = ChemblUtils(self.api).compound_dot_dict_to_obj(ch)
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
        return [self._code(lookup, compound, dots, 3), self._code(lookup, compound, dots, 4)]

    def _code(self, lookup: str, compound: ChemblCompound, dots: NestedDotDict, level: int):
        # 'level1': 'N', 'level1_description': 'NERVOUS SYSTEM', 'level2': 'N05', ...
        return AtcHit(
            None,
            compound.chid,
            compound.inchikey,
            lookup,
            compound.name,
            object_id=dots.get(f"level{level}"),
            object_name=dots.get(f"level{level}_description"),
            level=level,
        )


__all__ = ["AtcHit", "AtcSearch"]
