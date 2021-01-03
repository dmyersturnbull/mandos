import logging
from dataclasses import dataclass
from typing import Sequence
import re

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import ChemblCompound
from mandos.model.targets import Target
from mandos.search.protein_search import ProteinHit, ProteinSearch
from mandos.search.target_traversal_strategy import (
    TargetTraversalStrategy,
    TargetTraversalStrategies,
)

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
    src_id: str
    exact_target_id: str

    @property
    def predicate(self) -> str:
        return "activity"


class ActivitySearch(ProteinSearch[ActivityHit]):
    """
    Search for ``activity``.
    """

    @property
    def default_traversal_strategy(self) -> TargetTraversalStrategy:
        return TargetTraversalStrategies.strategy0(self.api)

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        def set_to_regex(values) -> str:
            return "(" + "|".join([f"(?:{re.escape(v)})" for v in values]) + ")"

        filters = dict(
            parent_molecule_chembl_id=parent_form.chid,
            assay_type__iregex=set_to_regex(self.config.allowed_assay_types),
            standard_relation__iregex=set_to_regex(self.config.allowed_relations),
            pchembl_value__isnull=False if self.config.require_pchembl else None,
            target_organism__isnull=False if self.config.require_taxon else None,
        )
        # I'd rather not figure out how the API interprets None, so remove them
        filters = {k: v for k, v in filters.items() if v is not None}
        return list(self.api.activity.filter(**filters))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: Target
    ) -> bool:
        if (
            data.get_as("data_validity_comment", lambda s: s.lower())
            in {s.lower() for s in self.config.banned_flags}
            or data.req_as("standard_relation", str) not in self.config.allowed_relations
            or data.req_as("assay_type", str) not in self.config.allowed_assay_types
            or data.get("target_tax_id") is None
            and self.config.require_taxon
            or data.get_as("target_tax_id", int) not in self.tax
            and self.config.require_taxon
            or data.get("pchembl_value") is None
            and self.config.require_pchembl
            or data.req_as("pchembl_value", float) < self.config.min_pchembl
            and self.config.require_pchembl
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
        if target.type.name.lower() not in {s.lower() for s in self.config.allowed_target_types}:
            logger.warning(f"Excluding {target} with type {target.type}")
            return False
        if self.config.require_confidence_score:
            if confidence_score is None or confidence_score < self.config.min_confidence_score:
                return False
            # Even if we supposedly allow the target type, it doesn't make sense for some confidence scores
            # Some of these are non-protein types]
            # And if it's unknown, we don't know what to do with it
            if (
                target.type.is_unknown
                or target.type.is_strange
                and self.config.min_confidence_score > 3
            ):
                logger.warning(f"Excluding {target} with type {target.type}")
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
                src_id=data.req_as("src_id", str),
                exact_target_id=data.req_as("target_chembl_id", str),
            )
        )


__all__ = ["ActivityHit", "ActivitySearch"]
