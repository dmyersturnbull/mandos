from dataclasses import dataclass
from typing import Sequence, Optional

from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class CtdGeneHit(PubchemHit):
    """"""

    taxon_id: Optional[int]
    taxon_name: Optional[str]


class CtdGeneSearch(PubchemSearch[CtdGeneHit]):
    """"""

    @property
    def data_source(self) -> str:
        return "Comparative Toxicogenomics Database (CTD)"

    def find(self, inchikey: str) -> Sequence[CtdGeneHit]:
        data = self.api.fetch_data(inchikey)
        return [
            CtdGeneHit(
                record_id=None,
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_id=str(data.cid),
                compound_name=data.name,
                predicate="gene interaction",
                object_id=dd.gene_name,
                object_name=dd.gene_name,
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
                taxon_id=dd.tax_id,
                taxon_name=dd.tax_name,
            )
            for dd in data.biomolecular_interactions_and_pathways.compound_gene_interactions
        ]


__all__ = ["CtdGeneHit", "CtdGeneSearch"]
