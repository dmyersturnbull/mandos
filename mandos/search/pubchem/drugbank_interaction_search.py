from typing import Optional, Sequence, Set, TypeVar

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_models import (
    DrugbankInteraction,
    DrugbankTargetType,
)

# noinspection PyProtectedMember
from mandos.model.concrete_hits import (
    DrugbankGeneralFunctionHit,
    DrugbankTargetHit,
    _DrugbankInteractionHit,
)
from mandos.search.pubchem import PubchemSearch

T = TypeVar("T", bound=_DrugbankInteractionHit, covariant=True)


# noinspection PyAbstractClass
class _DrugbankInteractionSearch(PubchemSearch[T]):
    def __init__(self, key: str, api: PubchemApi, target_types: Set[DrugbankTargetType]):
        super().__init__(key, api)
        self.target_types = target_types

    @classmethod
    def _get_obj(cls, dd: DrugbankInteraction) -> Optional[str]:
        raise NotImplementedError()

    def find(self, inchikey: str) -> Sequence[T]:
        data = self.api.fetch_data(inchikey)
        results = []
        for dd in data.biomolecular_interactions_and_pathways.drugbank_interactions:
            if dd.target_type in self.target_types:
                source = self._format_source(type=dd.target_type.name)
                predicate = self._format_predicate(
                    type=dd.target_type.name,
                    action="generic" if dd.action is None else dd.action,
                )
                obj = self._get_obj(dd)
                if obj is not None:
                    results.append(
                        self._create_hit(
                            c_id=str(data.cid),
                            c_origin=inchikey,
                            c_matched=data.names_and_identifiers.inchikey,
                            c_name=data.name,
                            data_source=source,
                            predicate=predicate,
                            object_id=obj,
                            object_name=obj,
                            gene_symbol=dd.gene_symbol,
                            protein_id=dd.protein_id,
                            target_type=dd.target_type.name,
                            target_name=dd.target_name,
                            general_function=dd.general_function,
                            cache_date=data.names_and_identifiers.modify_date,
                        )
                    )
        return results


class DrugbankTargetSearch(_DrugbankInteractionSearch[DrugbankTargetHit]):
    """ """

    @classmethod
    def _get_obj(cls, dd: DrugbankInteraction) -> Optional[str]:
        return dd.target_name


class DrugbankGeneralFunctionSearch(_DrugbankInteractionSearch[DrugbankGeneralFunctionHit]):
    """ """

    @classmethod
    def _get_obj(cls, dd: DrugbankInteraction) -> Optional[str]:
        return dd.general_function  # might be None


__all__ = [
    "DrugbankTargetSearch",
    "DrugbankGeneralFunctionSearch",
]
