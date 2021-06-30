import abc
from dataclasses import dataclass
from typing import Sequence, Set, Optional

from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support import ChemblCompound, AssayType
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.taxonomy import Taxonomy
from mandos.search.chembl._protein_search import ProteinHit, ProteinSearch, H


@dataclass(frozen=True, order=True, repr=True)
class _ActivityHit(ProteinHit):
    taxon_id: int
    taxon_name: str
    src_id: str


class _ActivitySearch(ProteinSearch[H], metaclass=abc.ABCMeta):
    """
    Search for ``activity``.
    """

    def __init__(
        self,
        key: str,
        api: ChemblApi,
        taxa: Sequence[Taxonomy],
        traversal: str,
        target_types: Set[str],
        min_conf_score: Optional[int],
        allowed_relations: Set[str],
        min_pchembl: Optional[float],
        banned_flags: Set[str],
        binds_cutoff: Optional[float] = None,
        does_not_bind_cutoff: Optional[float] = None,
    ):
        super().__init__(key, api, taxa, traversal, target_types, min_conf_score)
        self.allowed_relations = allowed_relations
        self.min_pchembl = min_pchembl
        self.banned_flags = banned_flags
        self.binds_cutoff = binds_cutoff
        self.does_not_bind_cutoff = does_not_bind_cutoff

    @classmethod
    def allowed_assay_types(cls) -> Set[str]:
        raise NotImplementedError()

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        filters = dict(
            parent_molecule_chembl_id=parent_form.chid,
            assay_type__iregex=self._set_to_regex(self.allowed_assay_types()),
            standard_relation__iregex=self._set_to_regex(self.allowed_relations),
            pchembl_value__isnull=None if self.min_pchembl is None else False,
            target_organism__isnull=None if len(self.taxa) == 0 else False,
        )
        # I'd rather not figure out how the API interprets None, so remove them
        filters = {k: v for k, v in filters.items() if v is not None}
        return list(self.api.activity.filter(**filters))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> bool:
        if (
            (
                data.get_as("data_validity_comment", lambda s: s.lower())
                in {s.lower() for s in self.banned_flags}
            )
            or (data.req_as("standard_relation", str) not in self.allowed_relations)
            or (data.req_as("assay_type", str) not in self.allowed_assay_types())
            or (len(self.taxa) > 0 and not self.is_in_taxa(data.get_as("target_tax_id", int)))
            or (self.min_pchembl is not None and data.get("pchembl_value") is None)
            or (
                self.min_pchembl is not None
                and data.req_as("pchembl_value", float) < self.min_pchembl
            )
        ):
            return False
        if data.get("data_validity_comment") is not None:
            logger.debug(
                f"Activity for {lookup} has flag '{data.get('data_validity_comment')} (ok)"
            )
        # The `target_organism` doesn't always match the `assay_organism`
        # Ex: see assay CHEMBL823141 / document CHEMBL1135642 for homo sapiens in xenopus laevis
        # However, it's often something like yeast expressing a human / mouse / etc receptor
        # So there's no need to filter by it
        assay = self.api.assay.get(data.req_as("assay_chembl_id", str))
        if target.type.name.lower() not in {s.lower() for s in self.allowed_target_types}:
            logger.debug(f"Excluding {target.name} with type {target.type}")
            return False
        confidence_score = assay.get("confidence_score")
        if self.min_confidence_score is not None:
            if confidence_score is None or confidence_score < self.min_confidence_score:
                return False
        # Some of these are non-protein types
        # And if it's unknown, we don't know what to do with it
        return True

    def _extract(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> NestedDotDict:
        # we know these exist from the query
        organism = data.req_as("target_organism", str)
        tax_id = data.req_as("target_tax_id", int)
        if len(self.taxa) == 0:
            tax_id, tax_name = tax_id, organism
        else:
            taxes = {tax.req(tax_id) for tax in self.taxa if tax.contains(tax_id)}
            tax = next(iter(taxes))
            if len(taxes) > 1:
                logger.warning(f"Multiple matches for taxon {tax_id}: {taxes}; using {tax}")
            if organism != tax.name:
                logger.warning(f"Target organism {organism} is not {tax.name}")
            tax_id = tax.id
            tax_name = tax.name
        return NestedDotDict(
            {
                **dict(
                    origin_inchikey=lookup,
                    matched_inchikey=compound.inchikey,
                    compound_id=compound.chid,
                    compound_name=compound.name,
                    taxon_id=tax_id,
                    taxon_name=tax_name,
                ),
                **data,
            }
        )


__all__ = ["_ActivitySearch", "_ActivityHit"]
