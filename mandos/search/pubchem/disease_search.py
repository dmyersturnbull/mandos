from dataclasses import dataclass
from typing import Sequence

from mandos.model import MiscUtils
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DiseaseHit(PubchemHit):
    evidence_type: str


class DiseaseSearch(PubchemSearch[DiseaseHit]):
    """ """

    @property
    def data_source(self) -> str:
        return "Comparative Toxicogenomics Database (CTD) :: diseases"

    def find(self, inchikey: str) -> Sequence[DiseaseHit]:
        data = self.api.fetch_data(inchikey)
        return [
            self._create_hit(
                inchikey=inchikey,
                c_id=str(data.cid),
                c_origin=inchikey,
                c_matched=data.names_and_identifiers.inchikey,
                c_name=data.name,
                predicate=f"disease:{dd.evidence_type}",
                statement=f"has {dd.evidence_type} evidence for",
                object_id=dd.disease_id,
                object_name=dd.disease_name,
            )
            for dd in data.associated_disorders_and_diseases.associated_disorders_and_diseases
        ]


__all__ = ["DiseaseHit", "DiseaseSearch"]
