from dataclasses import dataclass
from typing import Sequence

from mandos.model.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DgiHit(PubchemHit):
    """"""


@dataclass(frozen=True, order=True, repr=True)
class CgiHit(PubchemHit):
    """"""


class DgiSearch(PubchemSearch[DgiHit]):
    """"""

    def __init__(self, key: str, api: PubchemApi):
        super().__init__(key, api)

    @property
    def data_source(self) -> str:
        return "The Drug Gene Interaction Database (DGIdb)"

    def find(self, inchikey: str) -> Sequence[DgiHit]:
        data = self.api.fetch_data(inchikey)
        return [
            DgiHit(
                record_id=None,
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_id=str(data.cid),
                compound_name=data.name,
                predicate=f"interacts with gene (drug)",
                object_id=dd.gene_claim_id,
                object_name=dd.gene_name,
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
            )
            for dd in data.biomolecular_interactions_and_pathways.drug_gene_interactions
        ]


class CgiSearch(PubchemSearch[CgiHit]):
    """"""

    def __init__(self, key: str, api: PubchemApi):
        super().__init__(key, api)

    @property
    def data_source(self) -> str:
        return "The Drug Gene Interaction Database (DGIdb)"

    def find(self, inchikey: str) -> Sequence[DgiHit]:
        data = self.api.fetch_data(inchikey)
        return [
            DgiHit(
                record_id=None,
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_id=str(data.cid),
                compound_name=data.name,
                predicate=f"interacts with gene (compound)",
                object_id=dd.gene_name,
                object_name=dd.gene_name,
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
            )
            for dd in data.biomolecular_interactions_and_pathways.compound_gene_interactions
        ]


__all__ = ["DgiHit", "DgiSearch", "CgiHit", "CgiSearch"]
