import enum
import logging
from dataclasses import dataclass
from typing import Sequence, Optional, Set

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support import ChemblCompound
from mandos.model.chembl_support.chembl_targets import TargetFactory
from mandos.model.chembl_support.chembl_target_graphs import ChemblTargetGraph
from mandos.model.chembl_support.chembl_utils import ChemblUtils
from mandos.model.defaults import Defaults
from mandos.model.taxonomy import Taxonomy
from mandos.search.chembl import ChemblHit, ChemblSearch, H

logger = logging.getLogger("mandos")


class AssayType(enum.Enum):
    binding = enum.auto()
    functional = enum.auto()
    adme = enum.auto()
    physicochemical = enum.auto()

    @property
    def character(self) -> str:
        return {
            AssayType.binding: "B",
            AssayType.functional: "F",
            AssayType.adme: "A",
            AssayType.physicochemical: "P",
        }[self]


@dataclass(frozen=True, order=True, repr=True)
class FunctionalHit(ChemblHit):
    """
    An "activity" hit of type "F" for a compound.
    """

    taxon_id: int
    taxon_name: str
    source: str
    assay_type: AssayType
    tissue: Optional[str]
    cell_type: Optional[str]
    subcellular_region: Optional[str]

    @property
    def predicate(self) -> str:
        return "functional activity"


class FunctionalSearch(ChemblSearch[FunctionalHit]):
    """
    Search for ``activity`` of type "F".
    """

    def __init__(
        self,
        chembl_api: ChemblApi,
        tax: Taxonomy,
    ):
        super().__init__(chembl_api)
        self.taxon = tax

    def find(self, lookup: str) -> Sequence[H]:
        """

        Args:
            lookup:

        Returns:e

        """
        form = ChemblUtils(self.api).get_compound(lookup)
        results = self.query(form)
        hits = []
        for result in results:
            result = NestedDotDict(result)
            hits.extend(self.process(lookup, form, result))
        return hits

    def process(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> Sequence[H]:
        """

        Args:
            lookup:
            compound:
            data:

        Returns:

        """
        if data.get("target_chembl_id") is None:
            logger.debug(f"target_chembl_id missing from mechanism '{data}' for compound {lookup}")
            return []
        chembl_id = data["target_chembl_id"]
        target_obj = TargetFactory.find(chembl_id, self.api)
        if not self.should_include(lookup, compound, data, target_obj):
            return []
        return self.to_hit(lookup, compound, data, target_obj)

    def query(self, parent_form: ChemblCompound) -> Sequence[NestedDotDict]:
        filters = dict(
            parent_molecule_chembl_id=parent_form.chid,
            assay_type="F",
            target_organism__isnull=None if Defaults.chembl_functional_taxon is None else False,
        )
        # I'd rather not figure out how the API interprets None, so remove them
        filters = {k: v for k, v in filters.items() if v is not None}
        return list(self.api.activity.filter(**filters))

    def should_include(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> bool:
        if (
            data.get_as("data_validity_comment", lambda s: s.lower())
            in {s.lower() for s in Defaults.chembl_banned_flags}
        ) or (self.taxon is not None and data.get_as("target_tax_id", int) not in self.taxon):
            return False
        if data.get("data_validity_comment") is not None:
            logger.debug(
                f"Activity annotation for {lookup} has flag '{data.get('data_validity_comment')} (ok)"
            )
        return True

    def to_hit(
        self, lookup: str, compound: ChemblCompound, data: NestedDotDict, target: ChemblTargetGraph
    ) -> Sequence[FunctionalHit]:
        # these must match the constructor of the Hit,
        # EXCEPT for object_id and object_name, which come from traversal
        x = self._extract(lookup, compound, data)
        return [FunctionalHit(**x, object_id=target.chembl, object_name=target.name)]

    def _extract(self, lookup: str, compound: ChemblCompound, data: NestedDotDict) -> NestedDotDict:
        # we know these exist from the query
        organism = data.req_as("target_organism", str)
        tax_id = data.req_as("target_tax_id", int)
        tax = self.taxon.req(tax_id)
        if organism != tax.name:
            logger.warning(f"Target organism {organism} is not {tax.name}")
        assay = self.api.assay.get(data.req_as("assay_chembl_id", str))
        return NestedDotDict(
            dict(
                record_id=data.req_as("activity_id", str),
                compound_id=compound.chid,
                inchikey=compound.inchikey,
                compound_name=compound.name,
                compound_lookup=lookup,
                taxon_id=tax.id,
                taxon_name=tax.name,
                src_id=data.req_as("src_id", str),
            )
        )


__all__ = ["FunctionalHit", "FunctionalSearch", "AssayType"]
