from dataclasses import dataclass
from typing import Sequence

from mandos.model.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DgiHit(PubchemHit):
    """"""


class DgiSearch(PubchemSearch[DgiHit]):
    """"""

    def __init__(self, key: str, api: PubchemApi):
        super().__init__(key, api)

    @property
    def data_source(self) -> str:
        return "Drug Gene Interaction Database (DGIdb) :: drug/gene interactions"

    def find(self, inchikey: str) -> Sequence[DgiHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biomolecular_interactions_and_pathways.drug_gene_interactions:
            interactions = (
                ["interacts with"]
                if len(dd.interactions) == 0
                else [s + " for" for s in dd.interactions]
            )
            for interaction in interactions:
                results.append(
                    DgiHit(
                        record_id=None,
                        origin_inchikey=inchikey,
                        matched_inchikey=data.names_and_identifiers.inchikey,
                        compound_id=str(data.cid),
                        compound_name=data.name,
                        predicate=interaction,
                        object_id=dd.gene_claim_id,
                        object_name=dd.gene_name,
                        search_key=self.key,
                        search_class=self.search_class,
                        data_source=self.data_source,
                    )
                )
        return results


__all__ = ["DgiHit", "DgiSearch"]
