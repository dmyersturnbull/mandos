"""
DrugBank REST API.
"""

from __future__ import annotations

import abc
import logging
from typing import Iterator

from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger("mandos")


class DrugbankQueryByDrug(metaclass=abc.ABCMeta):
    def __getitem__(self, item: int) -> NestedDotDict:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[NestedDotDict]:
        raise NotImplementedError()


class DrugbankEndpoint(metaclass=abc.ABCMeta):
    """"""


class DrugbankDiscoveryEndpoint(DrugbankEndpoint):
    def drug(self, drug_id: str) -> NestedDotDict:
        raise NotImplementedError()

    def bonds(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def snps(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def bio_entity(self, entity_id: str) -> NestedDotDict:
        raise NotImplementedError()

    def polypeptide(self, polypeptide_id: str) -> NestedDotDict:
        raise NotImplementedError()


class DrugbankClinicalEndpoint(DrugbankEndpoint):
    def drug(self, drug_id: str) -> NestedDotDict:
        raise NotImplementedError()

    def categories(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def indications(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def ddis(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def adverse_effects(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def contraindications(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()

    def boxed_warnings(self, drug_id: str) -> DrugbankQueryByDrug:
        raise NotImplementedError()


class DrugbankApi(metaclass=abc.ABCMeta):
    @property
    def discovery(self) -> DrugbankDiscoveryEndpoint:
        raise NotImplementedError()

    @property
    def clinical(self) -> DrugbankClinicalEndpoint:
        raise NotImplementedError()


__all__ = [
    "DrugbankQueryByDrug",
    "DrugbankDiscoveryEndpoint",
    "DrugbankClinicalEndpoint",
    "DrugbankApi",
]
