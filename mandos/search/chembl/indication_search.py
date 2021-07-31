from __future__ import annotations

from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_utils import ChemblUtils
from mandos.search.chembl import ChemblSearch
from mandos.model.concrete_hits import IndicationHit


class IndicationSearch(ChemblSearch[IndicationHit]):
    """ """

    def __init__(self, key: str, api: ChemblApi, min_phase: int):
        super().__init__(key, api)
        self.min_phase = min_phase

    @property
    def data_source(self) -> str:
        return "ChEMBL :: indications"

    def find(self, lookup: str) -> Sequence[IndicationHit]:
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
        phase = indication.req_as("max_phase_for_ind", int)
        return self._create_hit(
            c_origin=lookup,
            c_matched=compound.inchikey,
            c_id=compound.chid,
            c_name=compound.name,
            predicate=f"trial:phase{phase}",
            object_id=indication.req_as("mesh_id", str),
            object_name=indication.req_as("mesh_heading", str).strip("\n"),
            max_phase=phase,
        )


__all__ = ["IndicationSearch"]
