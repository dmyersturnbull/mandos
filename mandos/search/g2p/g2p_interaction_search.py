from dataclasses import dataclass
from typing import Sequence

from mandos.model.apis.g2p_data import G2pData, G2pInteraction

from mandos.search.g2p import G2pSearch, G2pHit


@dataclass(frozen=True, order=True, repr=True)
class G2pInteractionHit(G2pHit):
    """ """

    action: str
    selective: str
    primary: str
    endogenous: str
    species: str
    affinity: float
    measurement: str


class G2pInteractionSearch(G2pSearch[G2pInteractionHit]):
    """ """

    @property
    def data_source(self) -> str:
        return "G2P :: interactions"

    def find(self, inchikey: str) -> Sequence[G2pInteractionHit]:
        ligand = self.api.fetch(inchikey)
        results = []
        for inter in ligand.interactions:
            results.append(self.process(inchikey, ligand, inter))
        return results

    def process(self, inchikey: str, ligand: G2pData, inter: G2pInteraction) -> G2pInteractionHit:
        predicate = f"{inter.action} at"
        return G2pInteractionHit(
            record_id=None,
            origin_inchikey=inchikey,
            matched_inchikey=ligand.inchikey,
            compound_id=str(ligand.g2pid),
            compound_name=ligand.name,
            predicate=predicate,
            object_id=inter.target_id,
            object_name=inter.target,
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source,
            action=inter.action,
            affinity=inter.affinity_median,
            measurement=inter.affinity_units,
            species=inter.target_species,
            primary=str(inter.primary_target),
            selective=str(inter.selectivity),
            endogenous=str(inter.endogenous),
        )


__all__ = ["G2pInteractionHit", "G2pInteractionSearch"]
