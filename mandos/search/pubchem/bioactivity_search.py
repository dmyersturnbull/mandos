import re
from dataclasses import dataclass
from typing import Sequence, Optional, Set

from loguru import logger

from mandos.model.pubchem_api import PubchemApi
from mandos.model.pubchem_support.pubchem_data import PubchemData
from mandos.model.pubchem_support.pubchem_models import Activity, Bioactivity
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class BioactivityHit(PubchemHit):
    """"""

    target_abbrev: Optional[str]
    activity: str
    assay_type: str
    micromolar: float
    relation: str
    species: Optional[str]
    compound_name_in_assay: str
    referrer: str


class BioactivitySearch(PubchemSearch[BioactivityHit]):
    """"""

    def __init__(
        self,
        key: str,
        api: PubchemApi,
        compound_name_must_match: bool,
    ):
        super().__init__(key, api)
        self.compound_name_must_match = compound_name_must_match

    @property
    def data_source(self) -> str:
        return "PubChem"

    def find(self, inchikey: str) -> Sequence[BioactivityHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biological_test_results.bioactivity:
            if not self.compound_name_must_match or dd.compound_name.lower() == data.name.lower():
                results.append(self.process(inchikey, data, dd))
        return results

    def process(self, inchikey: str, data: PubchemData, dd: Bioactivity) -> BioactivityHit:
        target_name, target_abbrev, species = dd.target_name_abbrev_species
        data_source = f"{self.data_source}: {dd.assay_ref} ({dd.assay_type})"
        if dd.activity in {Activity.inconclusive, Activity.unspecified}:
            predicate = "has " + dd.activity.name + " activity for"
        else:
            predicate = "is " + dd.activity.name + " against"
        return BioactivityHit(
            record_id=None,
            origin_inchikey=inchikey,
            matched_inchikey=data.names_and_identifiers.inchikey,
            compound_id=str(data.cid),
            compound_name=data.name,
            predicate=predicate,
            object_id=dd.gene_id,
            object_name=target_name,
            search_key=self.key,
            search_class=self.search_class,
            data_source=data_source,
            target_abbrev=target_abbrev,
            activity=dd.activity.name.lower(),
            assay_type=dd.assay_type,
            micromolar=dd.activity_value,
            relation=dd.activity_name,
            species=species,
            compound_name_in_assay=dd.compound_name,
            referrer=dd.assay_ref,
        )


__all__ = ["BioactivityHit", "BioactivitySearch"]
