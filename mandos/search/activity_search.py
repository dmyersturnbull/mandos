import logging
from dataclasses import dataclass
from typing import Sequence

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import AbstractHit, ChemblCompound, Search
from mandos.model.targets import TargetFactory, TargetType

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class ActivityHit(AbstractHit):
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

    def over(self, pchembl: float) -> bool:
        """

        Args:
            pchembl:

        Returns:

        """
        return self.pchembl >= float(pchembl)


class ActivitySearch(Search[ActivityHit]):
    """
    Search under ChEMBL "activity".
    """

    def find(self, lookup: str) -> Sequence[ActivityHit]:
        """

        Args:
            lookup:

        Returns:

        """
        form = self.get_compound(lookup)
        results = self.api.activity.filter(
            parent_molecule_chembl_id=form.chid,
            assay_type="B",
            standard_relation__iregex="(=|<|(?:<=))",
            pchembl_value__isnull=False,
            target_organism__isnull=False,
            assay_organism__isnull=False,
        )
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(lookup, form, result))
        return hits

    def process(
        self, lookup: str, compound: ChemblCompound, activity: NestedDotDict
    ) -> Sequence[ActivityHit]:
        """

        Args:
            lookup:
            compound:
            activity:

        Returns:

        """
        bad_flags = {
            "potential missing data",
            "potential transcription error",
            "outside typical range",
        }
        if (
            activity.get_as("data_validity_comment", lambda s: s.lower()) in bad_flags
            or activity.req_as("standard_relation", str) not in ["=", "<", "<="]
            or activity.req_as("assay_type", str) != "B"
            or activity.get_as("pchembl_value", float) is None
            or activity.get_as("target_tax_id", int) is None
            or activity.get_as("target_tax_id", int) not in self.tax
            or activity.req_as("pchembl_value", float) < self.config.min_pchembl
        ):
            return []
        # The `target_organism` doesn't always match the `assay_organism`
        # Ex: see assay CHEMBL823141 / document CHEMBL1135642 for homo sapiens in xenopus laevis
        # However, it's often something like yeast expressing a human / mouse / etc receptor
        # So there's no need to filter by it
        assay = self.api.assay.get(activity.req_as("assay_chembl_id", str))
        confidence_score = assay.req_as("confidence_score", int)
        if confidence_score < self.config.min_confidence_score:
            return []
        return self._traverse(lookup, compound, activity, assay)

    def _traverse(
        self, lookup: str, compound: ChemblCompound, activity: NestedDotDict, assay: NestedDotDict
    ) -> Sequence[ActivityHit]:
        """

        Args:
            lookup:
            compound:
            activity:

        Returns:

        """
        organism = activity.req_as("target_organism", str)
        tax_id = activity.req_as("target_tax_id", int)
        tax = self.tax.req(tax_id)
        if organism != tax.name:
            logger.error(f"Target organism {organism} is not {tax.name}")
        data = dict(
            record_id=activity.req_as("activity_id", str),
            compound_id=compound.chid,
            inchikey=compound.inchikey,
            compound_name=compound.name,
            compound_lookup=lookup,
            taxon_id=tax.id,
            taxon_name=tax.name,
            pchembl=activity.req_as("pchembl_value", float),
            std_type=activity.req_as("standard_type", str),
            src_id=activity.req_as("src_id", int),
            exact_target_id=activity.req_as("target_chembl_id", str),
        )
        target_obj = TargetFactory.find(activity.req_as("target_chembl_id", str), self.api)
        if target_obj.type == TargetType.unknown:
            logger.error(f"Target {target_obj} has type UNKNOWN")
            return []
        ancestor = target_obj.traverse_smart()
        return [ActivityHit(**data, object_id=ancestor.chembl, object_name=ancestor.name)]


__all__ = ["ActivityHit", "ActivitySearch"]
