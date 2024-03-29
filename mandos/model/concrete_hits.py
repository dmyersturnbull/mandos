from __future__ import annotations

import abc
import enum
from dataclasses import dataclass
from typing import Optional

from pocketutils.core.enums import CleverEnum
from pocketutils.tools.reflection_tools import ReflectionTools

from mandos.model.hits import AbstractHit


@dataclass(frozen=True, order=True, repr=True)
class ChemblHit(AbstractHit, metaclass=abc.ABCMeta):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class ProteinHit(ChemblHit, metaclass=abc.ABCMeta):
    """
    A protein target entry for a compound.
    """

    exact_target_id: str
    exact_target_name: str


@dataclass(frozen=True, order=True, repr=True)
class _ActivityHit(ProteinHit):
    taxon_id: int
    taxon_name: str
    src_id: str


@dataclass(frozen=True, order=True, repr=True)
class AtcHit(ChemblHit):
    """
    An ATC code found for a compound.
    """

    level: int


@dataclass(frozen=True, order=True, repr=True)
class BindingHit(_ActivityHit):
    """
    An "activity" hit for a compound.
    """

    pchembl: float
    std_type: str
    std_rel: str


@dataclass(frozen=True, order=True, repr=True)
class FunctionalHit(_ActivityHit):
    """
    An "activity" hit of type "F" for a compound.
    """

    tissue: Optional[str]
    cell_type: Optional[str]
    subcellular_region: Optional[str]


class GoType(CleverEnum):
    component = ()
    function = ()
    process = ()


@dataclass(frozen=True, order=True, repr=True)
class GoHit(ChemblHit, metaclass=abc.ABCMeta):
    """
    A mechanism entry for a compound.
    """

    go_type: str
    taxon_id: int
    taxon_name: str
    src_id: str
    pchembl: float
    std_type: str
    std_rel: str
    target_id: str
    target_name: str
    exact_target_id: str
    exact_target_name: str


@dataclass(frozen=True, order=True, repr=True)
class IndicationHit(ChemblHit):
    """
    An indication with a MESH term.
    """

    max_phase: int


@dataclass(frozen=True, order=True, repr=True)
class MechanismHit(ProteinHit):
    """
    A mechanism entry for a compound.
    """

    action_type: str
    description: str


@dataclass(frozen=True, order=True, repr=True)
class G2pHit(AbstractHit, metaclass=abc.ABCMeta):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class G2pInteractionHit(G2pHit):
    """ """

    action: str
    selective: str
    primary: str
    endogenous: str
    species: str
    affinity: float
    measurement: str


@dataclass(frozen=True, order=True, repr=True)
class PubchemHit(AbstractHit, metaclass=abc.ABCMeta):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class HmdbHit(AbstractHit, metaclass=abc.ABCMeta):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class AcuteEffectHit(PubchemHit):
    """ """

    organism: str
    human: bool
    test_type: str
    route: str
    effect: str
    mg_per_kg: float


@dataclass(frozen=True, order=True, repr=True)
class Ld50Hit(PubchemHit):
    """ """

    organism: str
    human: bool
    route: str


@dataclass(frozen=True, order=True, repr=True)
class BioactivityHit(PubchemHit):
    """ """

    target_abbrev: Optional[str]
    activity: str
    assay_type: str
    micromolar: float
    relation: str
    species: Optional[str]
    compound_name_in_assay: str
    referrer: str


@dataclass(frozen=True, order=True, repr=True)
class ComputedPropertyHit(PubchemHit):
    pass


@dataclass(frozen=True, order=True, repr=True)
class CoOccurrenceHit(PubchemHit, metaclass=abc.ABCMeta):
    intersect_count: int
    query_count: int
    neighbor_count: int


@dataclass(frozen=True, order=True, repr=True)
class DiseaseCoOccurrenceHit(CoOccurrenceHit):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class GeneCoOccurrenceHit(CoOccurrenceHit):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class ChemicalCoOccurrenceHit(CoOccurrenceHit):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class CtdGeneHit(PubchemHit):
    """ """

    taxon_id: Optional[int]
    taxon_name: Optional[str]


@dataclass(frozen=True, order=True, repr=True)
class DgiHit(PubchemHit):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class DiseaseHit(PubchemHit):
    evidence_type: str


@dataclass(frozen=True, order=True, repr=True)
class DrugbankDdiHit(PubchemHit):
    """ """

    type: str
    effect_target: Optional[str]
    change: Optional[str]
    description: str


@dataclass(frozen=True, order=True, repr=True)
class _DrugbankInteractionHit(PubchemHit):
    """ """

    gene_symbol: str
    protein_id: str
    target_type: str
    target_name: str
    general_function: str


@dataclass(frozen=True, order=True, repr=True)
class DrugbankTargetHit(_DrugbankInteractionHit):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class DrugbankGeneralFunctionHit(_DrugbankInteractionHit):
    """ """


@dataclass(frozen=True, order=True, repr=True)
class TrialHit(PubchemHit):
    phase: float
    status: str
    interventions: str


@dataclass(frozen=True, order=True, repr=True)
class TissueConcentrationHit(HmdbHit):
    micromolar: float
    ages: str
    sexes: str


@dataclass(frozen=True, order=True, repr=True)
class ChemblTargetPredictionHit(ChemblHit):
    """
    Predictions from ChEMBL's SAR.
    """

    taxon_id: int
    taxon_name: str
    exact_target_id: int
    exact_target_name: str
    threshold: float
    prediction: str
    confidence_set: int


@dataclass(frozen=True, order=True, repr=True)
class MetaHit(AbstractHit):
    """"""


HIT_CLASSES = ReflectionTools.subclass_dict(AbstractHit, concrete=True)
