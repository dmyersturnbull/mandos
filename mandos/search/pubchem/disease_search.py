import abc
from dataclasses import dataclass
from typing import Sequence

from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DiseaseHit(PubchemHit, metaclass=abc.ABCMeta):
    evidence_type: str

    @property
    def predicate(self) -> str:
        return f"has {self.evidence_type}"


class DiseaseSearch(PubchemSearch[DiseaseHit]):
    """"""

    def find(self, inchikey: str) -> Sequence[DiseaseHit]:
        data = self.api.fetch_data(inchikey)
        return [
            DiseaseHit(
                record_id=dd.gid,
                compound_id=str(data.cid),
                inchikey=data.names_and_identifiers.inchikey,
                compound_lookup=inchikey,
                compound_name=data.name,
                object_id=dd.disease_id,
                object_name=dd.disease_name,
                evidence_type=dd.evidence_type,
            )
            for dd in data.associated_disorders_and_diseases.associated_disorders_and_diseases
        ]


__all__ = ["DiseaseHit", "DiseaseSearch"]
