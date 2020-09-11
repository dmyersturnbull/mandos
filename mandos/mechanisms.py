import logging
from dataclasses import dataclass
from typing import Sequence, Set

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit
from mandos.taxonomy import Taxon, Taxonomy
from mandos.utils import Utils

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True)
class MechanismHit(AbstractHit):
    target_id: int
    target_name: str
    taxon: Taxon
    action_type: str
    src_id: int

    @property
    def predicate(self) -> str:
        return self.action_type


class MechanismSearch:
    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def find(self, compound: str) -> Sequence[MechanismHit]:
        c = Utils.get_compound(compound)
        results = Chembl.mechanism.filter(molecule_chembl_id=c.chid)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(compound, result))
        return hits
