from typing import Optional, Sequence, Set

from pocketutils.tools.common_tools import CommonTools

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_models import ClinicalTrial
from mandos.model.concrete_hits import TrialHit
from mandos.search.pubchem import PubchemSearch


class TrialSearch(PubchemSearch[TrialHit]):
    """ """

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
        # {std_status}:phase{std_phase}
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
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        data_source=self._format_source(
                            source=dd.source,
                            full_status=dd.status,
                            std_status=dd.mapped_status,
                            full_phase=dd.phase,
                            std_phase=dd.mapped_phase,
                        ),
                        predicate=self._format_predicate(
                            full_status=dd.status,
                            std_status=dd.mapped_status,
                            full_phase=dd.phase,
                            std_phase=dd.mapped_phase,
                        ),
                        object_id=did,
                        object_name=condition,
                        weight=self._weight(dd),
                        phase=dd.mapped_phase,
                        status=dd.mapped_status,
                        interventions=str(list(dd.interventions)),
                        cache_date=data.names_and_identifiers.modify_date,
                    )
                )
        return hits

    def _weight(self, dd: ClinicalTrial) -> float:
        return dd.mapped_phase


__all__ = ["TrialSearch"]
