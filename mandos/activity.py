import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, Search
from mandos.model.targets import Target, TargetType
from mandos.model.taxonomy import Taxon, Taxonomy
from mandos.model.utils import ChemblCompound, Utils

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class BindingHit(AbstractHit):
    target_id: int
    target_name: str
    taxon_id: int
    taxon_name: str
    pchembl: float
    std_type: str
    src_id: int
    exact_target_id: str

    @property
    def predicate(self) -> str:
        return "activity"

    def over(self, pchembl: float) -> bool:
        return self.pchembl >= float(pchembl)


class ActivitySearch(Search[BindingHit]):
    def find(self, lookup: str) -> Sequence[BindingHit]:
        form = Utils.get_compound(lookup)
        results = self.api.activity.filter(parent_molecule_chembl_id=form.chid)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(lookup, form, result))
        return hits

    def process(
        self, lookup: str, compound: ChemblCompound, activity: NestedDotDict
    ) -> Sequence[BindingHit]:
        if (
            activity.get("data_validity_comment") is not None
            or activity["standard_relation"] not in ["=", "<", "<="]
            or activity["assay_type"] != "B"
            or activity.get("pchembl_value") is None
            or activity.get("target_organism") is None
            or activity["target_organism"] not in self.tax
        ):
            return []
        return self._traverse(lookup, compound, activity)

    def _traverse(
        self, lookup: str, compound: ChemblCompound, activity: NestedDotDict
    ) -> Sequence[BindingHit]:
        data = dict(
            record_id=activity["activity_id"],
            compound_id=compound.chid_int,
            inchikey=compound.inchikey,
            compound_name=compound.name,
            compound_lookup=lookup,
            taxon_id=self.tax[activity["target_organism"]].id,
            taxon_name=self.tax[activity["target_organism"]].name,
            pchembl=float(activity["pchembl_value"]),
            std_type=activity["standard_type"],
            src_id=int(activity["src_id"]),
            exact_target_id=activity["target_chembl_id"],
        )
        target_obj = Target.find(activity["target_chembl_id"])
        if target_obj.type == TargetType.unknown:
            logger.error(f"Target {target_obj} has type UNKNOWN")
            return []
        ancestor = target_obj.traverse_smart()
        return [BindingHit(**data, target_id=ancestor.id, target_name=ancestor.name)]
