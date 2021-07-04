from dataclasses import dataclass
from typing import Sequence, Set

from mandos.model import MiscUtils
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class ComputedPropertyHit(PubchemHit):
    pass


class ComputedPropertySearch(PubchemSearch[ComputedPropertyHit]):
    """ """

    def __init__(self, key: str, api: PubchemApi, descriptors: Set[str]):
        super().__init__(key, api)
        self.api = api
        self.descriptors = descriptors

    @property
    def data_source(self) -> str:
        return "PubChem :: computed properties"

    def find(self, inchikey: str) -> Sequence[ComputedPropertyHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        # we're really not going to have a case where there are two keys --
        # one with different capitalization or punctuation
        descriptors = {self._standardize_key(s) for s in self.descriptors}
        for dd in data.chemical_and_physical_properties.computed:
            if self._standardize_key(dd.key) in descriptors:
                results.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        predicate="has " + dd.key.lower(),
                        statement="property:" + dd.key.lower(),
                        object_id=dd.value,
                        object_name=dd.value,
                    )
                )
        return results

    def _standardize_key(self, key: str) -> str:
        return key.replace(" ", "").replace("-", "").replace("_", "").replace(".", "").lower()


__all__ = ["ComputedPropertyHit", "ComputedPropertySearch"]
