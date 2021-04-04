import abc
import re
from dataclasses import dataclass
from typing import Sequence, Set, Optional

from pocketutils.tools.common_tools import CommonTools

from mandos.model.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class TrialHit(PubchemHit):
    phase: float
    status: str
    interventions: str


class TrialSearch(PubchemSearch[TrialHit]):
    """"""

    @property
    def data_source(self) -> str:
        return "ClinicalTrials.gov :: trials"

    def __init__(
        self,
        key: str,
        api: PubchemApi,
        min_phase: Optional[float],
        statuses: Optional[Set[str]],
        require_compound_as_intervention: bool,
    ):
        super().__init__(key, api)
        self.min_phase = min_phase
        self.statuses = statuses
        self.require_compound_as_intervention = require_compound_as_intervention

    def find(self, inchikey: str) -> Sequence[TrialHit]:
        data = self.api.fetch_data(inchikey)
        hits = []
        for dd in data.drug_and_medication_information.clinical_trials:
            if self.min_phase is not None and dd.mapped_phase < self.min_phase:
                continue
            if self.statuses is not None and dd.mapped_status not in self.statuses:
                continue
            if self.require_compound_as_intervention and data.name not in {
                s.lower() for s in dd.interventions
            }:
                continue
            for did, condition in CommonTools.zip_list(dd.disease_ids, dd.conditions):
                hits.append(
                    TrialHit(
                        record_id=dd.ctid,
                        compound_id=str(data.cid),
                        origin_inchikey=inchikey,
                        matched_inchikey=data.names_and_identifiers.inchikey,
                        compound_name=data.name,
                        predicate=f"was a {dd.mapped_status} {dd.mapped_phase} trial intervention for",
                        object_id=did,
                        object_name=condition,
                        search_key=self.key,
                        search_class=self.search_class,
                        data_source=self.data_source,
                        phase=dd.mapped_phase,
                        status=dd.mapped_status,
                        interventions=" || ".join(dd.interventions),
                    )
                )
        return hits


__all__ = ["TrialHit", "TrialSearch"]
