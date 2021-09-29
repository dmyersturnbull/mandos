from typing import Sequence

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.pubchem_support.pubchem_models import Bioactivity
from mandos.model.concrete_hits import BioactivityHit
from mandos.search.pubchem import PubchemSearch


class BioactivitySearch(PubchemSearch[BioactivityHit]):
    """ """

    def __init__(
        self,
        key: str,
        api: PubchemApi,
        compound_name_must_match: bool,
    ):
        super().__init__(key, api)
        self.compound_name_must_match = compound_name_must_match

    def find(self, inchikey: str) -> Sequence[BioactivityHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biological_test_results.bioactivity:
            if not self.compound_name_must_match or dd.compound_name.lower() == data.name.lower():
                results.append(self.process(inchikey, data, dd))
        return results

    def process(self, inchikey: str, data: PubchemData, dd: Bioactivity) -> BioactivityHit:
        target_name, target_abbrev, species = dd.target_name_abbrev_species
        action = dd.activity.name.lower()
        source = self._format_source(
            assay_type=dd.assay_type,
            species=species,
        )
        predicate = self._format_predicate(
            action=action,
            assay_type=dd.assay_type,
            species=species,
        )
        return self._create_hit(
            inchikey=inchikey,
            c_id=str(data.cid),
            c_origin=inchikey,
            c_matched=data.names_and_identifiers.inchikey,
            c_name=data.name,
            data_source=source,
            predicate=predicate,
            object_id=dd.gene_id,
            object_name=target_name,
            target_abbrev=target_abbrev,
            activity=action,
            assay_type=dd.assay_type,
            micromolar=dd.activity_value,
            relation=dd.activity_name,
            species=species,
            compound_name_in_assay=dd.compound_name,
            referrer=dd.assay_ref,
        )


__all__ = ["BioactivitySearch"]
