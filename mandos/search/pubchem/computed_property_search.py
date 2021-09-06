from typing import Sequence, Set

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.search.pubchem import PubchemSearch
from mandos.model.concrete_hits import ComputedPropertyHit


class ComputedPropertySearch(PubchemSearch[ComputedPropertyHit]):
    """ """

    def __init__(self, key: str, api: PubchemApi, descriptors: Set[str]):
        super().__init__(key, api)
        self.api = api
        self.descriptors = descriptors

    def find(self, inchikey: str) -> Sequence[ComputedPropertyHit]:
        data = self.api.fetch_data(inchikey)
        results = []
        # we're really not going to have a case where there are two keys --
        # one with different capitalization or punctuation
        descriptors = {self._standardize_key(s) for s in self.descriptors}
        for dd in data.chemical_and_physical_properties.computed:
            if self._standardize_key(dd.key) in descriptors:
                source = self._format_source(key=dd.key.lower())
                predicate = self._format_predicate(key=dd.key.lower())
                results.append(
                    self._create_hit(
                        inchikey=inchikey,
                        c_id=str(data.cid),
                        c_origin=inchikey,
                        c_matched=data.names_and_identifiers.inchikey,
                        c_name=data.name,
                        data_source=source,
                        predicate=predicate,
                        object_id=dd.value,
                        object_name=dd.value,
                    )
                )
        return results

    def _standardize_key(self, key: str) -> str:
        return key.replace(" ", "").replace("-", "").replace("_", "").replace(".", "").lower()


__all__ = ["ComputedPropertySearch"]
