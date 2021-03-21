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
    compound_name_in_assay: str
    referrer: str


class BioactivitySearch(PubchemSearch[BioactivityHit]):
    """"""

    def __init__(
        self,
        key: str,
        api: PubchemApi,
        answers: Set[Activity],
        assay_types: Set[AssayType],
        min_micromolar: Optional[float],
        max_micromolar: Optional[float],
        relations: Set[str],
        compound_name_must_match: bool,
    ):
        super().__init__(key, api)
        self.answers = answers
        self.assay_types = assay_types
        self.min_micromolar, self.max_micromolar = min_micromolar, max_micromolar
        self.relations = relations
        self.compound_name_must_match = compound_name_must_match

    @property
    def data_source(self) -> str:
        return "PubChem"

    def find(self, inchikey: str) -> Sequence[BioactivityHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biological_test_results.bioactivity:
            results.append(self.process(inchikey, data, dd))
        return results

    def process(self, inchikey: str, data: PubchemData, dd: Bioactivity) -> BioactivityHit:
        return BioactivityHit(
            record_id=None,
            origin_inchikey=inchikey,
            matched_inchikey=data.names_and_identifiers.inchikey,
            compound_id=str(data.cid),
            compound_name=data.name,
            predicate=f"bioactivity",
            object_id=dd.gene_id,
            object_name=dd.target_name,
            search_key=self.key,
            search_class=self.search_class,
            data_source=self.data_source + " : " + dd.assay_ref,
            activity=dd.activity.name.lower(),
            confirmatory=dd.assay_type is AssayType.confirmatory,
            micromolar=dd.activity_value,
            relation=dd.activity_name,
            compound_name_in_assay=dd.compound_name,
            referrer=dd.assay_ref,
        )


__all__ = ["BioactivityHit", "BioactivitySearch"]
