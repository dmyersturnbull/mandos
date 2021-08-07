from typing import Sequence, Set, TypeVar

from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_support.pubchem_models import DrugbankInteraction, DrugbankTargetType
from mandos.search.pubchem import PubchemSearch
from mandos.model.concrete_hits import _DrugbankInteractionHit

T = TypeVar("T", bound=_DrugbankInteractionHit, covariant=True)


# noinspection PyAbstractClass
class _DrugbankInteractionSearch(PubchemSearch[T]):
    def __init__(self, key: str, api: PubchemApi, target_types: Set[DrugbankTargetType]):
        super().__init__(key, api)
        self.target_types = target_types

    @classmethod
    def _get_obj(cls, dd: DrugbankInteraction) -> str:
        raise NotImplementedError()

    def find(self, inchikey: str) -> Sequence[T]:
        data = self.api.fetch_data(inchikey)
        return [
            self._create_hit(
                inchikey=inchikey,
                c_id=str(data.cid),
                c_origin=inchikey,
                c_matched=data.names_and_identifiers.inchikey,
                c_name=data.name,
                predicate=self._get_predicate(dd),
                object_id=self._get_obj(dd),
                object_name=self._get_obj(dd),
                gene_symbol=dd.gene_symbol,
                protein_id=dd.protein_id,
                target_type=dd.target_type.name,
                target_name=dd.target_name,
                general_function=dd.general_function,
            )
            for dd in data.biomolecular_interactions_and_pathways.drugbank_interactions
            if dd.target_type in self.target_types
        ]

    @classmethod
    def _get_predicate(cls, dd: DrugbankInteraction) -> str:
        action = "generic" if dd.action is None else dd.action
        return dd.target_type.name + ":" + action


class DrugbankTargetSearch(_DrugbankInteractionSearch[_DrugbankInteractionHit]):
    """ """

    @property
    def data_source(self) -> str:
        return "DrugBank :: target interactions"

    @classmethod
    def _get_obj(cls, dd: DrugbankInteraction) -> str:
        return dd.target_name


class DrugbankGeneralFunctionSearch(_DrugbankInteractionSearch[_DrugbankInteractionHit]):
    """ """

    @property
    def data_source(self) -> str:
        return "DrugBank :: non-target interactions"

    @classmethod
    def _get_obj(cls, dd: DrugbankInteraction) -> str:
        return dd.target_name if dd.general_function is None else dd.general_function


__all__ = [
    "DrugbankTargetSearch",
    "DrugbankGeneralFunctionSearch",
]
