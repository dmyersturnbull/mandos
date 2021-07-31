from typing import Sequence

from mandos.search.pubchem import PubchemSearch
from mandos.model.concrete_hits import DiseaseHit


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
                object_id=dd.disease_id,
                object_name=dd.disease_name,
            )
            for dd in data.associated_disorders_and_diseases.associated_disorders_and_diseases
        ]


__all__ = ["DiseaseSearch"]
