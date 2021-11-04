"""
Model of ChEMBL targets and a hierarchy between them as a directed acyclic graph (DAG).
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Mapping, Optional, Set

import decorateme
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.enums import CleverEnum
from pocketutils.core.exceptions import LookupFailedError
from urllib3.util.retry import MaxRetryError

from mandos.model.apis.chembl_api import ChemblApi


class TargetNotFoundError(LookupFailedError):
    """ """


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
    oligosaccharide = enum.auto()
    cell_line = enum.auto()
    macromolecule = enum.auto()
    subcellular = enum.auto()
    tissue = enum.auto()
    unknown = enum.auto()

    @classmethod
    def resolve(cls, types: str) -> Set[TargetType]:
        """
        Resolve a bunch of target types in a comma-separated list.
        Allows for special types prefixed by an ``@``: ``@all``, ``@known``, ``@protein``, ``@molecular``,
        and ``@nonmolecular``.

        Args:
            types: A string like ``'@protein,nucleic_acid``
        """
        found = set()
        for st in types.split(","):
            st = st.strip()
            if st == "@all":
                match = TargetType.all_types()
            elif st == "@any":
                match = TargetType.all_types()
            elif st == "@known":
                match = {s for s in TargetType.all_types() if not s.is_unknown}
            elif st == "@protein":
                match = TargetType.protein_types()
            elif st == "@molecular":
                match = TargetType.molecular_types()
            elif st == "@nonmolecular":
                match = TargetType.nonmolecular_types()
            else:
                match = {TargetType.of(st)}
            for m in match:
                found.add(m)
        return found

    @classmethod
    def special_type_names(cls) -> Mapping[str, str]:
        return {
            "@all": "all types",
            "@any": "all types",
            "@known": "all types except unknown",
            "@protein": ", ".join([s.name.replace("_", " ") for s in cls.protein_types()]),
            "@molecular": ", ".join([s.name.replace("_", " ") for s in cls.molecular_types()]),
            "@nonmolecular": ", ".join(
                [s.name.replace("_", " ") for s in cls.nonmolecular_types()]
            ),
        }

    @classmethod
    def _unmatched_type(cls) -> TargetType:
        # we'll overload the "unknown" value in case ChEMBL adds more types
        return cls.unknown

    @classmethod
    def protein_types(cls) -> Set[TargetType]:
        """
        Returns the target types that are expressly proteins.
        Specifically, single proteins, protein complexes, protein complex groups, and protein families.
        This does **not** include protein-protein interactions, chimeric proteins,
        protein-nucleic acid complexes, or selectivity groups.
        """
        return {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
        }

    @classmethod
    def molecular_types(cls) -> Set[TargetType]:
        """
        Returns the types that are either "molecular entities", including proteins, metals, nucleic acids, and
        protein/nucleic acid complexes, or groups of them, including protein families and protein complex groups.
        This excludes types like tissues, cell lines, and selectivity groups.
        """
        return {
            TargetType.single_protein,
            TargetType.protein_family,
            TargetType.protein_complex,
            TargetType.protein_complex_group,
            TargetType.nucleic_acid,
            TargetType.protein_nucleic_acid_complex,
            TargetType.metal,
            TargetType.small_molecule,
            TargetType.macromolecule,
            TargetType.oligosaccharide,
        }

    @classmethod
    def nonmolecular_types(cls) -> Set[TargetType]:
        """
        Complement of ``molecular_types``.
        """
        return {t for t in TargetType.all_types() if not t.is_molecular}

    @classmethod
    def all_types(cls) -> Set[TargetType]:
        return set(TargetType)  # here for symmetry

    @property
    def is_protein(self) -> bool:
        """
        Whether this type is a "protein".
        Specifically, single proteins, protein complexes, protein complex groups, and protein families.
        This does **not** include protein-protein interactions, chimeric proteins,
        protein-nucleic acid complexes, or selectivity groups.
        """
        return self in self.__class__.protein_types()

    @property
    def is_molecular(self) -> bool:
        """
        Whether this type is a "molecular entity" or superset (e.g. protein family or complex group).

        Does not include 'unknown'.
        """
        return self in self.__class__.molecular_types()

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


@decorateme.auto_obj()
class TargetFactory:
    """
    Factory for ``Target`` that injects a ``ChemblApi``.
    """

    def __init__(self, api: ChemblApi):
        self.api = api

    def find(self, chembl: str) -> ChemblTarget:
        """
        Finds.

        Args:
            chembl:

        Returns:
            A ``Target`` instance from a newly created subclass of that class
        """
        try:
            targets = self.api.target.filter(target_chembl_id=chembl)
        except MaxRetryError:
            raise TargetNotFoundError(f"Not found: target {chembl}")
        if len(targets) != 1:
            raise AssertionError(f"Found {len(targets)} targets for {chembl}")
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
    "ConfidenceLevel",
]
