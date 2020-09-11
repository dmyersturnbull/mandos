import logging
from dataclasses import dataclass
from typing import Sequence, Set

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit
from mandos.targets import Target, TargetType
from mandos.taxonomy import Taxon, Taxonomy
from mandos.utils import Utils

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True)
class BindingHit(AbstractHit):
    target_id: int
    target_name: str
    taxon: Taxon
    pchembl: float
    std_type: str
    src_id: int

    @property
    def predicate(self) -> str:
        return "activity"

    def over(self, pchembl: float) -> bool:
        return self.pchembl >= float(pchembl)


class ActivitySearch:
    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def find(self, compound: str) -> Sequence[BindingHit]:
        c = Utils.get_compound(compound)
        results = Chembl.activity.filter(molecule_chembl_id=c.chid)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(compound, result))
        return hits

    def process(self, compound: str, activity: NestedDotDict) -> Sequence[BindingHit]:
        if (
            activity.get("data_validity_comment") is not None
            or activity["standard_relation"] not in ["=", "<", "<="]
            or activity["assay_type"] != "B"
            or activity.get("pchembl_value") is None
            or activity.get("target_organism") is None
            or activity["target_organism"] not in self._tax
        ):
            return []
        return self._traverse(compound, activity)

    def _traverse(self, compound: str, activity: NestedDotDict) -> Sequence[BindingHit]:
        data = dict(
            activity_id=activity["activity_id"],
            compound_id=int(activity["molecule_chembl_id"].replace("CHEMBL", "")),
            compound_name=activity.get(
                "molecule_pref_name", "CHEMBL" + activity["molecule_chembl_id"]
            ),
            compound_lookup=compound,
            taxon=self._tax[activity["target_organism"]],
            pchembl=float(activity["pchembl_value"]),
            std_type=activity["standard_type"],
            src_id=int(activity["src_id"]),
        )
        target_obj = Target.find(activity["molecule_chembl_id"])
        links = target_obj.traverse_smart()
        return [BindingHit(**data, target_id=link.id, target_name=link.name) for link in links]
