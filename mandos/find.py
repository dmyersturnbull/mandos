import logging
from dataclasses import dataclass
from typing import Any, Generator, Mapping, Optional, Sequence, Set

from chembl_webresource_client.new_client import new_client as Chembl

from mandos.model import Target, TargetType, Taxon, Taxonomy
from mandos.utils import NestedDotDict

logger = logging.getLogger("mandos")


@dataclass(order=True)
class BindingHit:
    activity_id: int
    compound_id: int
    compound_lookup: str
    compound_name: str
    target_id: int
    target_name: str
    taxon: Taxon
    pchembl: float
    std_type: str
    src_id: int

    def over(self, pchembl: float):
        return self.pchembl >= float(pchembl)


class BindingSearch:
    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def find(self, compound: str) -> Sequence[BindingHit]:
        compound_id, compound_inchikey, compound_name = self._get_compound(compound)
        results = Chembl.activity.filter(molecule_chembl_id=compound_id)
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
        links: Set[Target] = {
            linked
            for linked in target_obj.traverse(
                {
                    TargetType.single_protein,
                    TargetType.protein_complex,
                    TargetType.protein_complex_group,
                }
            )
            if linked.type in {TargetType.single_protein, TargetType.protein_complex_group}
        }
        return [BindingHit(**data, target_id=link.id, target_name=link.name) for link in links]

    def _get_target(self, chembl: str) -> NestedDotDict:
        targets = Chembl.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
        return NestedDotDict(targets[0])

    def _get_compound(self, inchikey: str):
        ch = NestedDotDict(Chembl.molecule.get(inchikey))
        chid = ch["molecule_chembl_id"]
        inchikey = ch["molecule_structures"]["standard_inchi_key"]
        name = ch["pref_name"]
        return chid, inchikey, name
