from typing import Sequence

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemSearch
from mandos.model.concrete_hits import DgiHit


class DgiSearch(PubchemSearch[DgiHit]):
    """ """

    def __init__(self, key: str, api: PubchemApi):
        super().__init__(key, api)

    def find(self, inchikey: str) -> Sequence[DgiHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biomolecular_interactions_and_pathways.drug_gene_interactions:
            if len(dd.interactions) == 0:
                interactions = ["generic"]
            else:
                interactions = dd.interactions
            for interaction in interactions:
                source = self._format_source()
                predicate = self._format_predicate(type=interaction)
                results.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        data_source=source,
                        predicate=predicate,
                        object_id=dd.gene_claim_id,
                        object_name=dd.gene_name,
                    )
                )
        return results


__all__ = ["DgiSearch"]
