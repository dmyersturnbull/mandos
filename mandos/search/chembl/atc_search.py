from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_api import ChemblApi
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


class AtcSearch(ChemblSearch[AtcHit]):
    """"""

    def __init__(self, key: str, levels: Set[int], api: ChemblApi):
        super().__init__(key, api)
        self.levels = levels

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
        found = []
        for level in sorted(self.levels):
            found.append(self._code(lookup, compound, dots, level))
        return found

    def _code(self, lookup: str, compound: ChemblCompound, dots: NestedDotDict, level: int):
        # 'level1': 'N', 'level1_description': 'NERVOUS SYSTEM', 'level2': 'N05', ...
        return AtcHit(
            None,
            origin_inchikey=lookup,
            matched_inchikey=compound.inchikey,
            compound_id=compound.chid,
            compound_name=compound.name,
            predicate=f"ATC L{level} code",
            object_id=dots.get(f"level{level}"),
            object_name=dots.get(f"level{level}_description"),
            search_key=self.key,
            search_class=self.search_name,
            data_source=self.data_source,
            level=level,
        )


__all__ = ["AtcHit", "AtcSearch"]
