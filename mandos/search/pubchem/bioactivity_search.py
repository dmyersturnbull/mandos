from dataclasses import dataclass
from typing import Optional, Sequence

from mandos.model import MiscUtils
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.apis.pubchem_support.pubchem_models import Activity, Bioactivity
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class BioactivityHit(PubchemHit):
    """ """

    target_abbrev: Optional[str]
    activity: str
    assay_type: str
    micromolar: float
    relation: str
    species: Optional[str]
    compound_name_in_assay: str
    referrer: str


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

    @property
    def data_source(self) -> str:
        return "PubChem :: bioassays"

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
        predicate = f"bioactivity:{dd.activity.name.lower()}"
        if dd.activity in {Activity.inconclusive, Activity.unspecified}:
            statement = "has " + dd.activity.name + " activity for"
        else:
            statement = "is " + dd.activity.name + " against"
        return self._create_hit(
            inchikey=inchikey,
            c_id=str(data.cid),
            c_origin=inchikey,
            c_matched=data.names_and_identifiers.inchikey,
            c_name=data.name,
            predicate=predicate,
            statement=statement,
            object_id=dd.gene_id,
            object_name=target_name,
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
