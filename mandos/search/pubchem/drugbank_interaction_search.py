from dataclasses import dataclass
from typing import Sequence, TypeVar, Set

from mandos.model.pubchem_api import PubchemApi
from mandos.model.pubchem_support.pubchem_models import DrugbankTargetType
from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class _DrugbankInteractionHit(PubchemHit):
    """"""

    gene_symbol: str
    protein_id: str
    target_type: str
    target_name: str
    general_function: str
    specific_function: str


@dataclass(frozen=True, order=True, repr=True)
class DrugbankTargetHit(_DrugbankInteractionHit):
    """"""


@dataclass(frozen=True, order=True, repr=True)
class DrugbankGeneralFunctionHit(_DrugbankInteractionHit):
    """"""


T = TypeVar("T", bound=_DrugbankInteractionHit, covariant=True)


class _DrugbankInteractionSearch(PubchemSearch[T]):
    def __init__(self, key: str, api: PubchemApi, target_types: Set[DrugbankTargetType]):
        super().__init__(key, api)
        self.target_types = target_types

    """"""

    @property
    def data_source(self) -> str:
        return "DrugBank"

    @classmethod
    def _attr(cls):
        raise NotImplementedError()

    def find(self, inchikey: str) -> Sequence[T]:
        data = self.api.fetch_data(inchikey)
        # noinspection PyPep8Naming
        H = self.__class__.get_h()
        return [
            H(
                record_id=dd.record_id,
                origin_inchikey=inchikey,
                matched_inchikey=data.names_and_identifiers.inchikey,
                compound_id=str(data.cid),
                compound_name=data.name,
                predicate=dd.target_type.name + " :: " + dd.action + " on",
                object_id=dd.protein_id,
                object_name=getattr(dd, self.__class__._attr()),
                search_key=self.key,
                search_class=self.search_class,
                data_source=self.data_source,
                gene_symbol=dd.gene_symbol,
                protein_id=dd.protein_id,
                target_name=dd.target_name,
                general_function=dd.general_function,
                specific_function=dd.specific_function,
            )
            for dd in data.biomolecular_interactions_and_pathways.drugbank_interactions
            if dd.target_type in self.target_types
        ]


class DrugbankTargetSearch(_DrugbankInteractionSearch[_DrugbankInteractionHit]):
    """"""

    @classmethod
    def _attr(cls):
        return "targetname"


class DrugbankGeneralFunctionSearch(_DrugbankInteractionSearch[_DrugbankInteractionHit]):
    """"""

    @classmethod
    def _attr(cls):
        return "generalfunction"


__all__ = [
    "DrugbankTargetHit",
    "DrugbankGeneralFunctionHit",
    "DrugbankTargetSearch",
    "DrugbankGeneralFunctionSearch",
]
