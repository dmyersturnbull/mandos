import abc
from dataclasses import dataclass
from typing import Sequence

from mandos.model.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DiseaseHit(PubchemHit):
    evidence_type: str


class DiseaseSearch(PubchemSearch[DiseaseHit]):
    """"""

    @property
    def data_source(self) -> str:
        return "Comparative Toxicogenomics Database (CTD) :: diseases"

    def find(self, inchikey: str) -> Sequence[DiseaseHit]:
        data = self.api.fetch_data(inchikey)
        return [
            DiseaseHit(
                record_id=dd.gid,
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_id=str(data.cid),
                compound_name=data.name,
                predicate=f"has {dd.evidence_type} evidence for",
                object_id=dd.disease_id,
                object_name=dd.disease_name,
                evidence_type=dd.evidence_type,
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
            )
            for dd in data.associated_disorders_and_diseases.associated_disorders_and_diseases
        ]


__all__ = ["DiseaseHit", "DiseaseSearch"]
