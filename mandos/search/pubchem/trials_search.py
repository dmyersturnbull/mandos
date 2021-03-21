import abc
from dataclasses import dataclass
from typing import Sequence, Set, Optional

from pocketutils.tools.common_tools import CommonTools

from mandos.model.pubchem_api import PubchemApi
from mandos.model.pubchem_support.pubchem_models import ClinicalTrialsGovUtils
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class TrialHit(PubchemHit):
    phase: float
    status: str
    interventions: Sequence[str]

    @property
    def predicate(self) -> str:
        return f"has phase-{self.phase} clinical trial"


class TrialSearch(PubchemSearch[TrialHit]):
    """"""

    @property
    def data_source(self) -> str:
        return "ClinicalTrials.gov"

    def __init__(self, key: str, api: PubchemApi, min_phase: float, statuses: Set[str]):
        super().__init__(key, api)
        self.min_phase = min_phase
        self.statuses = statuses

    def find(self, inchikey: str) -> Sequence[TrialHit]:
        data = self.api.fetch_data(inchikey)
        hits = []
        for dd in data.drug_and_medication_information.clinical_trials:
            if (self.min_phase is None or dd.mapped_phase >= self.min_phase) and (
                self.statuses is None or dd.mapped_status in self.statuses
            ):
                for did, condition in CommonTools.zip_list(dd.disease_ids, dd.conditions):
                    hits.append(
                        TrialHit(
                            record_id=dd.ctid,
                            compound_id=str(data.cid),
                            origin_inchikey=inchikey,
                            matched_inchikey=data.names_and_identifiers.inchikey,
                            compound_name=data.name,
                            predicate=f"{dd.mapped_status} {dd.mapped_phase} trial intervention",
                            object_id=did,
                            object_name=condition,
                            search_key=self.key,
                            search_class=self.search_class,
                            data_source=self.data_source,
                            phase=dd.mapped_phase,
                            status=dd.mapped_status,
                            interventions=list(dd.interventions),
                        )
                    )
        return hits


__all__ = ["TrialHit", "TrialSearch"]
