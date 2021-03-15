"""
Model of ChEMBL targets and a hierarchy between them as a directed acyclic graph (DAG).
"""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import Optional, Set

from urllib3.util.retry import MaxRetryError
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import CleverEnum
from mandos.model.chembl_api import ChemblApi

logger = logging.getLogger(__package__)


class TargetNotFoundError(ValueError):
    """"""


@enum.unique
class ConfidenceLevel(CleverEnum):
    non_curated = 0
    non_molecular = 1
    # SKIP 2!! There is no 2
    non_protein = 3
    multiple_homologous_proteins = 4
    multiple_direct_proteins = 5
    homologous_protein_complex_subunits = 6
    direct_protein_complex_subunits = 7
    homologous_single_protein = 8
    direct_single_protein = 9


@enum.unique
class TargetType(CleverEnum):
    """
    Enum corresponding to the ChEMBL API field ``target.target_type``.
    """

    single_protein = enum.auto()
    protein_family = enum.auto()
    protein_complex = enum.auto()
    protein_complex_group = enum.auto()
    selectivity_group = enum.auto()
    protein_protein_interaction = enum.auto()
    nucleic_acid = enum.auto()
    chimeric_protein = enum.auto()
    protein_nucleic_acid_complex = enum.auto()
    metal = enum.auto()
    small_molecule = enum.auto()
    subcellular = enum.auto()
    unknown = enum.auto()

    @classmethod
    def _unmatched_type(cls) -> TargetType:
        # we'll allow an "unknown" value in case ChEMBL adds more types
        return cls.unknown

    @classmethod
    def protein_types(cls) -> Set[TargetType]:
        """
        Returns the target types that are expressly proteins.
        Specifically, single proteins, protein complexes, protein complex groups, and protein families.
        This does **not** include protein-protein interactions, chimeric proteins,
        protein-nucleic acid complexes, or selectivity groups.
        """
        return {s for s in cls if s.is_protein}

    @classmethod
    def all_types(cls) -> Set[TargetType]:
        return set(TargetType)  # here for symmetry

    @property
    def is_traversable(self) -> bool:
        """
        Returns the target types that can have relationships defined on them.
        Note that this may not match ChEMBL's own definition --
        there may be types (e.g. protein_protein_interaction) that have relationships.
        Those rare types are not included here.
        """
        return self in {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
            TargetType.selectivity_group,
        }

    @property
    def is_protein(self) -> bool:
        """
        Whether this type is a "protein".
        Specifically, single proteins, protein complexes, protein complex groups, and protein families.
        This does **not** include protein-protein interactions, chimeric proteins,
        protein-nucleic acid complexes, or selectivity groups.
        """
        return self in {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
        }

    @property
    def is_unknown(self) -> bool:
        """
        Returns whether this is the "unknown" type.
        In principle, this could have a more involved meaning.
        """
        return self == TargetType.unknown


@dataclass(frozen=True, order=True, repr=True)
class ChemblTarget:
    """
    A target from ChEMBL, from the ``target`` table.

    Attributes:
        chembl: The CHEMBL ID, starting with 'CHEMBL'
        name: The preferred name (``pref_target_name``)
        type: From the ``target_type`` ChEMBL field
    """

    chembl: str
    name: Optional[str]
    type: TargetType


class TargetFactory:
    """
    Factory for ``Target`` that injects a ``ChemblApi``.
    """

    def __init__(self, api: ChemblApi):
        self.api = api

    def find(self, chembl: str) -> ChemblTarget:
        """

        Args:
            chembl:

        Returns:
            A ``Target`` instance from a newly created subclass of that class
        """

        try:
            targets = self.api.target.filter(target_chembl_id=chembl)
        except MaxRetryError:
            raise TargetNotFoundError(f"Failed to find target {chembl}")
        assert len(targets) == 1, f"Found {len(targets)} targets for {chembl}"
        target = NestedDotDict(targets[0])
        return ChemblTarget(
            chembl=target["target_chembl_id"],
            name=target.get("pref_name"),
            type=TargetType.of(target["target_type"]),
        )


__all__ = [
    "TargetType",
    "TargetFactory",
    "TargetNotFoundError",
    "ChemblTarget",
]
