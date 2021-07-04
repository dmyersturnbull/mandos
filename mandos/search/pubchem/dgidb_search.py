from dataclasses import dataclass
from typing import Sequence

from mandos.model import MiscUtils
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DgiHit(PubchemHit):
    """ """


class DgiSearch(PubchemSearch[DgiHit]):
    """ """

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
                [("interaction:generic", "interacts with")]
                if len(dd.interactions) == 0
                else [("interaction" + s, s + " for") for s in dd.interactions]
            )
            for predicate, statement in interactions:
                results.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        predicate=predicate,
                        statement=statement,
                        object_id=dd.gene_claim_id,
                        object_name=dd.gene_name,
                    )
                )
        return results


__all__ = ["DgiHit", "DgiSearch"]
