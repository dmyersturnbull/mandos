from typing import AbstractSet, Optional, Sequence, Set

from pocketutils.tools.common_tools import CommonTools

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_models import (
    ClinicalTrial,
    ClinicalTrialSimplifiedStatus,
)
from mandos.model.concrete_hits import TrialHit
from mandos.search.pubchem import PubchemSearch


class TrialSearch(PubchemSearch[TrialHit]):
    """ """

    def __init__(
        self,
        key: str,
        api: PubchemApi,
        min_phase: Optional[float],
        statuses: Optional[AbstractSet[ClinicalTrialSimplifiedStatus]],
        explicit: bool,
    ):
        super().__init__(key, api)
        self.min_phase = min_phase
        self.statuses = statuses
        self.explicit = explicit

    def find(self, inchikey: str) -> Sequence[TrialHit]:
        data = self.api.fetch_data(inchikey)
        hits = []
        # {std_status}:phase{std_phase}
        for dd in data.drug_and_medication_information.clinical_trials:
            if self.min_phase is not None and dd.mapped_phase.score < self.min_phase:
                continue
            if self.statuses is not None and dd.mapped_status.name not in self.statuses:
                continue
            if self.explicit and data.name not in {s.lower() for s in dd.interventions}:
                continue
            for did, condition in CommonTools.zip_list(dd.disease_ids, dd.conditions):
                hits.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        data_source=self._format_source(
                            source=dd.source,
                            full_status=dd.status,
                            std_status=dd.mapped_status.name,
                            full_phase=dd.phase,
                            std_phase=dd.mapped_phase.name,
                        ),
                        predicate=self._format_predicate(
                            full_status=dd.status,
                            std_status=dd.mapped_status.name,
                            full_phase=dd.phase,
                            std_phase=dd.mapped_phase.name,
                        ),
                        object_id=did,
                        object_name=condition,
                        weight=self._weight(dd),
                        phase=dd.mapped_phase.name,
                        status=dd.mapped_status.name,
                        interventions=str(list(dd.interventions)),
                        cache_date=data.names_and_identifiers.modify_date,
                    )
                )
        return hits

    def _weight(self, dd: ClinicalTrial) -> float:
        return dd.mapped_phase.score


__all__ = ["TrialSearch"]
