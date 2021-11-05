import abc
from typing import Optional, Sequence, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_support import ChemblCompound
from mandos.model.apis.chembl_support.chembl_activity import DataValidityComment
from mandos.model.apis.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.taxonomy_caches import LazyTaxonomy
from mandos.model.utils.setup import logger
from mandos.search.chembl._protein_search import H, ProteinSearch


class _ActivitySearch(ProteinSearch[H], metaclass=abc.ABCMeta):
    """
    Search for ``activity``.
    """

    def __init__(
        self,
        key: str,
        api: ChemblApi,
        taxa: LazyTaxonomy,
        traversal: str,
        target_types: Set[str],
        min_conf_score: Optional[int],
        relations: Set[str],
        min_pchembl: Optional[float],
        binds_cutoff: Optional[float] = None,
    ):
        super().__init__(key, api, taxa, traversal, target_types, min_conf_score)
        self.allowed_relations = relations
        self.min_pchembl = min_pchembl
        self.binds_cutoff = binds_cutoff

    @classmethod
    def assay_type(cls) -> str:
        raise NotImplementedError()

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        filters = dict(
            parent_molecule_chembl_id=parent_form.chid,
            assay_type=self.assay_type(),
            pchembl_value__isnull=None if self.min_pchembl is None else False,
            target_organism__isnull=None if len(self.taxa.get) == 0 else False,
        )
        # I'd rather not figure out how the API interprets None, so remove them
        filters = {k: v for k, v in filters.items() if v is not None}
        return list(self.api.activity.filter(**filters))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> bool:
        bad_flags = {
            DataValidityComment.potential_missing_data,
            DataValidityComment.potential_transcription_error,
            DataValidityComment.outside_typical_range,
            DataValidityComment.author_confirmed_error,
        }
        if (
            (data.get_as("data_validity_comment", lambda s: s.lower()) in bad_flags)
            or (data.req_as("standard_relation", str) not in self.allowed_relations)
            or (data.req_as("assay_type", str) != self.assay_type())
            or (
                self.taxa.get is not None and data.get_as("target_tax_id", int) not in self.taxa.get
            )
            or (self.min_pchembl is not None and data.get("pchembl_value") is None)
            or (
                self.min_pchembl is not None
                and data.req_as("pchembl_value", float) < self.min_pchembl
            )
        ):
            logger.trace(f"Excluding {data}")
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
            logger.debug(
                f"Excluding {target.name} with type {target.type}"
                + f" (compound {compound.chid} [{compound.inchikey}])"
            )
            return False
        confidence_score = assay.get("confidence_score")
        if self.min_confidence_score is not None and (
            confidence_score is None or confidence_score < self.min_confidence_score
        ):
            logger.trace(f"Excluding {data} with confidence {confidence_score}")
            return False
        # Some of these are non-protein types
        # And if it's unknown, we don't know what to do with it
        return True

    def _extract(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> NestedDotDict:
        # we know these exist from the query
        organism = data.req_as("target_organism", str)
        tax_id = data.req_as("target_tax_id", int)
        if len(self.taxa.get) == 0:
            tax_id, tax_name = tax_id, organism
        else:
            tax = self.taxa.get.get(tax_id)
            if organism != tax.scientific_name:
                logger.warning(f"Target organism {organism} is not {tax.scientific_name}")
            tax_id = tax.id
            tax_name = tax.scientific_name
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


__all__ = ["_ActivitySearch"]
