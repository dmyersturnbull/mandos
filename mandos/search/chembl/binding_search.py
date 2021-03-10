import logging
from dataclasses import dataclass
from typing import Sequence, Set, Optional
import re

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import ChemblCompound
from mandos.model.chembl_support.chembl_targets import ChemblTarget
from mandos.model.defaults import Defaults
from mandos.model.taxonomy import Taxonomy
from mandos.search.chembl._protein_search import ProteinHit, ProteinSearch
from mandos.search.chembl.target_traversal import (
    TargetTraversalStrategy,
    TargetTraversalStrategies,
)

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True)
class BindingHit(ProteinHit):
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


class BindingSearch(ProteinSearch[BindingHit]):
    """
    Search for ``activity`` of type "B".
    """

    def __init__(
        self,
        chembl_api: ChemblApi,
        tax: Taxonomy,
        traversal_strategy: str,
        allowed_target_types: Set[str],
        min_confidence_score: Optional[int],
        allowed_relations: Set[str],
        min_pchembl: float,
        banned_flags: Set[str],
    ):
        super().__init__(chembl_api, tax, traversal_strategy)
        self.allowed_target_types = allowed_target_types
        self.min_confidence_score = min_confidence_score
        self.allowed_relations = allowed_relations
        self.min_pchembl = min_pchembl
        self.banned_flags = banned_flags

    @property
    def default_traversal_strategy(self) -> TargetTraversalStrategy:
        return TargetTraversalStrategies.strategy0(self.api)

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        def set_to_regex(values) -> str:
            return "(" + "|".join([f"(?:{re.escape(v)})" for v in values]) + ")"

        filters = dict(
            parent_molecule_chembl_id=parent_form.chid,
            assay_type="B",
            standard_relation__iregex=set_to_regex(self.allowed_relations),
            pchembl_value__isnull=False,
            target_organism__isnull=None if self.taxonomy is None else False,
        )
        # I'd rather not figure out how the API interprets None, so remove them
        filters = {k: v for k, v in filters.items() if v is not None}
        return list(self.api.activity.filter(**filters))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTarget
    ) -> bool:
        if (
            (
                data.get_as("data_validity_comment", lambda s: s.lower())
                in {s.lower() for s in self.banned_flags}
            )
            or (data.req_as("standard_relation", str) not in self.allowed_relations)
            or (data.req_as("assay_type", str) != "B")
            or (
                self.taxonomy is not None and data.get_as("target_tax_id", int) not in self.taxonomy
            )
            or (data.get("pchembl_value") is None)
            or (data.req_as("pchembl_value", float) < self.min_pchembl)
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
        if target.type.name.lower() not in {s.lower() for s in self.allowed_target_types}:
            logger.warning(f"Excluding {target} with type {target.type}")
            return False
        if self.min_confidence_score is not None:
            if confidence_score is None or confidence_score < self.min_confidence_score:
                return False
            # Some of these are non-protein types
            # And if it's unknown, we don't know what to do with it
        return True

    def to_hit(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTarget
    ) -> Sequence[BindingHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        x = self._extract(lookup, compound, data)
        return [BindingHit(**x, object_id=target.chembl, object_name=target.name)]

    def _extract(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> NestedDotDict:
        # we know these exist from the query
        if self.taxonomy is None:
            tax = None
        else:
            organism = data.req_as("target_organism", str)
            tax_id = data.req_as("target_tax_id", int)
            tax = self.taxonomy.req(tax_id)
            if organism != tax.name:
                logger.warning(f"Target organism {organism} is not {tax.name}")
        return NestedDotDict(
            dict(
                record_id=data.req_as("activity_id", str),
                compound_id=compound.chid,
                inchikey=compound.inchikey,
                compound_name=compound.name,
                compound_lookup=lookup,
                taxon_id=None if tax is None else tax.id,
                taxon_name=None if tax is None else tax.name,
                pchembl=data.req_as("pchembl_value", float),
                std_type=data.req_as("standard_type", str),
                src_id=data.req_as("src_id", str),
                exact_target_id=data.req_as("target_chembl_id", str),
            )
        )


__all__ = ["BindingHit", "BindingSearch"]
