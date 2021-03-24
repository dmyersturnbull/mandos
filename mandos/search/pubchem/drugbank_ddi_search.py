from dataclasses import dataclass
from typing import Sequence

from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DrugbankDdiHit(PubchemHit):
    """"""

    description: str


class DrugbankDdiSearch(PubchemSearch[DrugbankDdiHit]):
    """"""

    @property
    def data_source(self) -> str:
        return "DrugBank"

    def find(self, inchikey: str) -> Sequence[DrugbankDdiHit]:
        data = self.api.fetch_data(inchikey)
        return [
            DrugbankDdiHit(
                record_id=None,
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_id=str(data.cid),
                compound_name=data.name,
                predicate="ddi",
                object_id=dd.drug_drugbank_id,
                object_name=dd.drug_drugbank_id,
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
                description=dd.description,
            )
            for dd in data.biomolecular_interactions_and_pathways.drugbank_ddis
        ]


__all__ = ["DrugbankDdiHit", "DrugbankDdiSearch"]
