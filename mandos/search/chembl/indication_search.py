from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import ChemblCompound
from mandos.model.chembl_support.chembl_utils import ChemblUtils
from mandos.search.chembl import ChemblHit, ChemblSearch

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True)
class IndicationHit(ChemblHit):
    """
    An indication with a MESH term.
    """

    max_phase: int

    @property
    def predicate(self) -> str:
        return f"phase-{self.max_phase} trial"


class IndicationSearch(ChemblSearch[IndicationHit]):
    """"""

    def __init__(self, chembl_api: ChemblApi, min_phase: int):
        super().__init__(chembl_api)
        self.min_phase = min_phase

    def find(self, lookup: str) -> Sequence[IndicationHit]:
        """

        Args:
            lookup:

        Returns:

        """
        # 'atc_classifications': ['S01HA01', 'N01BC01', 'R02AD03', 'S02DA02']
        # 'indication_class': 'Anesthetic (topical)'
        ch = ChemblUtils(self.api).get_compound_dot_dict(lookup)
        compound = ChemblUtils(self.api).compound_dot_dict_to_obj(ch)
        inds = self.api.drug_indication.filter(parent_molecule_chembl_id=compound.chid)
        hits = []
        for ind in inds:
            if ind.req_as("max_phase_for_ind", int) >= self.min_phase:
                hits.append(self.process(lookup, compound, ind))
        return hits

    def process(
        self, lookup: str, compound: ChemblCompound, indication: NestedDotDict
    ) -> IndicationHit:
        """

        Args:
            lookup:
            compound:
            indication:

        Returns:

        """
        return IndicationHit(
            indication.req_as("drugind_id", str),
            compound.chid,
            compound.inchikey,
            lookup,
            compound.name,
            object_id=indication.req_as("mesh_id", str),
            object_name=indication.req_as("mesh_heading", str).strip("\n"),
            max_phase=indication.req_as("max_phase_for_ind", int),
        )


__all__ = ["IndicationHit", "IndicationSearch"]
