import re
from dataclasses import dataclass
from typing import Sequence, Optional, Set

from mandos.model.pubchem_api import PubchemApi
from mandos.model.pubchem_support.pubchem_data import PubchemData
from mandos.model.pubchem_support.pubchem_models import Activity, AssayType, Bioactivity
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class BioactivityHit(PubchemHit):
    """"""

    activity: str
    confirmatory: bool
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
        assay_types: Set[AssayType],
        compound_name_must_match: bool,
    ):
        super().__init__(key, api)
        self.assay_types = assay_types
        self.compound_name_must_match = compound_name_must_match

    @property
    def data_source(self) -> str:
        return "PubChem"

    def find(self, inchikey: str) -> Sequence[BioactivityHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biological_test_results.bioactivity:
            if (
                not self.compound_name_must_match or dd.compound_name.lower() == data.name.lower()
            ) and dd.assay_type in self.assay_types:
                results.append(self.process(inchikey, data, dd))
        return results

    def process(self, inchikey: str, data: PubchemData, dd: Bioactivity) -> BioactivityHit:
        # strip off the species name
        match = re.compile(r"^(.+?)\([^)]+\)?$").fullmatch(dd.target_name)
        target = match.group(1).strip()
        species = None if match.group(2).strip() == "" else match.group(2).strip()
        return BioactivityHit(
            record_id=None,
            origin_inchikey=inchikey,
            matched_inchikey=data.names_and_identifiers.inchikey,
            compound_id=str(data.cid),
            compound_name=data.name,
            predicate=dd.activity.name.lower(),
            object_id=dd.gene_id,
            object_name=target,
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source + ":" + dd.assay_ref,
            activity=dd.activity.name.lower(),
            confirmatory=dd.assay_type is AssayType.confirmatory,
            micromolar=dd.activity_value,
            relation=dd.activity_name,
            species=species,
            compound_name_in_assay=dd.compound_name,
            referrer=dd.assay_ref,
        )


__all__ = ["BioactivityHit", "BioactivitySearch"]
