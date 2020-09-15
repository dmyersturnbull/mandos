from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from mandos.model import AbstractHit, ChemblCompound, Search
from mandos.model.atc_codes import AtcCode

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class AtcHit(AbstractHit):
    """
    An ATC code found for a compound.
    """

    atc: AtcCode
    src_id: int

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
        """

        Args:
            lookup:
            compound:
            atc:

        Returns:

        """
        # TODO get from file
        return []
