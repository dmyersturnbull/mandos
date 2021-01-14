from __future__ import annotations

import abc
import enum
import logging
import re
from dataclasses import dataclass
from typing import Sequence, Type, Union, FrozenSet, Optional, TypeVar, Any

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, Search
from mandos.chembl_api import ChemblApi
from mandos.model.settings import Settings
from mandos.model.taxonomy import Taxonomy
from mandos.pubchem_api import (
    CachingPubchemApi,
    QueryingPubchemApi,
    PubchemData,
    TitleAndSummary,
    RelatedRecords,
    ChemicalAndPhysicalProperties,
    DrugAndMedicationInformation,
    PharmacologyAndBiochemistry,
    SafetyAndHazards,
    Toxicity,
    AssociatedDisordersAndDiseases,
    Literature,
    BiomolecularInteractionsAndPathways,
    Classification,
)


@dataclass(frozen=True, order=True, repr=True)
class PubchemClassHit(AbstractHit):
    @property
    def predicate(self) -> str:
        return "is in"


H = TypeVar("H", bound=AbstractHit, covariant=True)


class PubchemSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, chembl_api: ChemblApi, config: Settings, tax: Taxonomy):
        super().__init__(chembl_api, config, tax)
        self.pubchem_api = CachingPubchemApi(config.cache_path, QueryingPubchemApi(), compress=True)

    def find(self, lookup: str) -> Sequence[H]:
        data = self.pubchem_api.fetch_data(lookup)
        return self.process(lookup, data)

    def process(self, lookup: str, data: PubchemData) -> Sequence[H]:
        raise NotImplementedError()


class PubchemSearchFactory:

    pattern = re.compile(r"(?<!^)(?=[A-Z])")

    @classmethod
    def cat(
        cls, full_field, name: Optional[str] = None, object_field: Optional[str] = None
    ) -> Type[PubchemSearch]:
        clazz_name, field_name = str(full_field).split(" ", 3)[-2].split(".")
        clazz_name = PubchemSearchFactory.pattern.sub("_", clazz_name.__name__).lower()
        if name is None:
            name = field_name.replace("_", " ")

        class MyClassSearch(PubchemSearch[PubchemClassHit]):
            def process(self, lookup: str, data: PubchemData) -> Sequence[PubchemClassHit]:
                values = getattr(getattr(data, clazz_name), field_name)
                if object_field is not None:
                    values = frozenset([getattr(x, object_field) for x in values])
                if not isinstance(values, frozenset):
                    values = frozenset({values})
                hits = []
                for value in values:
                    """
                    record_id: Optional[str]
                    compound_id: str
                    inchikey: str
                    compound_lookup: str
                    compound_name: str
                    object_id: str
                    object_name: str
                    """
                    hit = PubchemClassHit(
                        record_id=None,
                        compound_id=str(data.cid),
                        inchikey=data.chemical_and_physical_properties.inchikey,
                        compound_lookup=lookup,
                        compound_name=data.name,
                        object_id=str(value),
                        object_name=str(value),
                    )
                return hits

        MyClassSearch.__name__ = name
        return MyClassSearch


F = PubchemSearchFactory
P = PubchemData

DeaClassSearch = F.cat(DrugAndMedicationInformation.dea_class)
DeaScheduleSearch = F.cat(DrugAndMedicationInformation.dea_schedule)
HsdbUsesSearch = F.cat(DrugAndMedicationInformation.hsdb_uses)
ClinicalTrialsSearch = F.cat(DrugAndMedicationInformation.clinical_trials)
