import abc
from dataclasses import dataclass
from typing import Sequence

from pocketutils.tools.common_tools import CommonTools

from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class TrialHit(PubchemHit, metaclass=abc.ABCMeta):
    phase: int
    status: str
    interventions: Sequence[str]

    @property
    def predicate(self) -> str:
        return f"has phase-{self.phase} clinical trial"


class TrialSearch(PubchemSearch[TrialHit]):
    """"""

    def find(self, inchikey: str) -> Sequence[TrialHit]:
        data = self.api.fetch_data(inchikey)
        hits = []
        for dd in data.drug_and_medication_information.clinical_trials:
            for did, condition in CommonTools.zip_list(dd.disease_ids, dd.conditions):
                hits.append(
                    TrialHit(
                        record_id=dd.ctid,
                        compound_id=str(data.cid),
                        inchikey=data.names_and_identifiers.inchikey,
                        compound_lookup=inchikey,
                        compound_name=data.name,
                        object_id=did,
                        object_name=condition,
                        phase=dd.known_phase,
                        status=dd.known_status,
                        interventions=list(dd.interventions),
                    )
                )
        return hits


__all__ = ["TrialHit", "TrialSearch"]
