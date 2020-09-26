import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import ChemblCompound
from mandos.model.targets import Target
from mandos.search.protein_search import ProteinHit, ProteinSearch

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class ActivityHit(ProteinHit):
    """
    An "activity" hit for a compound.
    """

    taxon_id: int
    taxon_name: str
    pchembl: float
    std_type: str
    src_id: int
    exact_target_id: str

    @property
    def predicate(self) -> str:
        return "activity"


class ActivitySearch(ProteinSearch[ActivityHit]):
    """
    Search for ``activity``.
    """

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        return list(
            self.api.activity.filter(
                parent_molecule_chembl_id=parent_form.chid,
                assay_type="B",
                standard_relation__iregex="(=|<|(?:<=))",
                pchembl_value__isnull=False,
                target_organism__isnull=False,
            )
        )

    def should_include(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> bool:
        bad_flags = {
            "potential missing data",
            "potential transcription error",
            "outside typical range",
        }
        if (
            data.get_as("data_validity_comment", lambda s: s.lower()) in bad_flags
            or data.req_as("standard_relation", str) not in ["=", "<", "<="]
            or data.req_as("assay_type", str) != "B"
            or data.get("target_tax_id") is None
            or data.get_as("target_tax_id", int) not in self.tax
            or data.get("pchembl_value") is None
            or data.req_as("pchembl_value", float) < self.config.min_pchembl
        ):
            return False
        if data.get("data_validity_comment") is not None:
            logger.warning(
                f"Activity annotation for {lookup} has flag '{data.get('data_validity_comment')} (ok)"
            )
        # The `target_organism` doesn't always match the `assay_organism`
        # Ex: see assay CHEMBL823141 / document CHEMBL1135642 for homo sapiens in xenopus laevis
        # However, it's often something like yeast expressing a human / mouse / etc receptor
        # So there's no need to filter by it
        assay = self.api.assay.get(data.req_as("assay_chembl_id", str))
        confidence_score = assay.get("confidence_score")
        if confidence_score is None or confidence_score < self.config.min_confidence_score:
            return False
        return True

    def to_hit(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: Target
    ) -> Sequence[ActivityHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        x = self._extract(lookup, compound, data)
        return [ActivityHit(**x, object_id=target.chembl, object_name=target.name)]

    def _extract(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> NestedDotDict:
        # we know these exist from the query
        organism = data.req_as("target_organism", str)
        tax_id = data.req_as("target_tax_id", int)
        tax = self.tax.req(tax_id)
        if organism != tax.name:
            logger.warning(f"Target organism {organism} is not {tax.name}")
        return NestedDotDict(
            dict(
                record_id=data.req_as("activity_id", str),
                compound_id=compound.chid,
                inchikey=compound.inchikey,
                compound_name=compound.name,
                compound_lookup=lookup,
                taxon_id=tax.id,
                taxon_name=tax.name,
                pchembl=data.req_as("pchembl_value", float),
                std_type=data.req_as("standard_type", str),
                src_id=data.req_as("src_id", int),
                exact_target_id=data.req_as("target_chembl_id", str),
            )
        )


__all__ = ["ActivityHit", "ActivitySearch"]
