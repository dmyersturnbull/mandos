from typing import Sequence

from mandos.model.apis.g2p_support.g2p_data import G2pData, G2pInteraction
from mandos.model.concrete_hits import G2pInteractionHit
from mandos.search.g2p import G2pSearch


class G2pInteractionSearch(G2pSearch[G2pInteractionHit]):
    """ """

    def find(self, inchikey: str) -> Sequence[G2pInteractionHit]:
        ligand = self.api.fetch(inchikey)
        results = []
        for inter in ligand.interactions:
            results.append(self.process(inchikey, ligand, inter))
        return results

    def process(self, inchikey: str, ligand: G2pData, inter: G2pInteraction) -> G2pInteractionHit:
        source = self._format_source(species=inter.target_species)
        predicate = self._format_predicate(
            primary=inter.primary_target,
            species=inter.target_species,
            endogenous=inter.endogenous,
            selective=inter.selectivity,
            action=inter.action,
        )
        return self._create_hit(
            c_origin=inchikey,
            c_matched=ligand.inchikey,
            c_id=str(ligand.g2pid),
            c_name=ligand.name,
            data_source=source,
            predicate=predicate,
            object_id=inter.target_id,
            object_name=inter.target,
            action=inter.action,
            affinity=inter.affinity_median,
            measurement=inter.affinity_units,
            species=inter.target_species,
            primary=str(inter.primary_target),
            selective=str(inter.selectivity),
            endogenous=str(inter.endogenous),
        )


__all__ = ["G2pInteractionSearch"]
