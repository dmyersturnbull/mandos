from typing import Sequence

from mandos.model.concrete_hits import DiseaseHit
from mandos.search.pubchem import PubchemSearch


class DiseaseSearch(PubchemSearch[DiseaseHit]):
    """ """

    def find(self, inchikey: str) -> Sequence[DiseaseHit]:
        data = self.api.fetch_data(inchikey)
        return [
            self._create_hit(
                data_source=self._format_source(evidence=dd.evidence_type),
                inchikey=inchikey,
                c_id=str(data.cid),
                c_origin=inchikey,
                c_matched=data.names_and_identifiers.inchikey,
                c_name=data.name,
                predicate=self._format_predicate(evidence=dd.evidence_type),
                object_id=dd.disease_id,
                object_name=dd.disease_name,
            )
            for dd in data.associated_disorders_and_diseases.associated_disorders_and_diseases
        ]


__all__ = ["DiseaseSearch"]
