from dataclasses import dataclass
from typing import List, Optional
import enum


class TrueFalseUnknown(enum.Enum):
    true = enum.auto()
    false = enum.auto()
    unknown = enum.auto()

    @classmethod
    def parse(cls, s: str):
        tf_map = {
            "t": TrueFalseUnknown.true,
            "f": TrueFalseUnknown.false,
            "true": TrueFalseUnknown.true,
            "false": TrueFalseUnknown.false,
        }
        return tf_map.get(s.lower().strip(), TrueFalseUnknown.unknown)


@dataclass
class G2pInteraction:
    target: str
    target_id: str
    target_gene_symbol: str
    target_uniprot: str
    target_species: str
    ligand_id: int
    type: str
    action: str
    selectivity: TrueFalseUnknown
    endogenous: TrueFalseUnknown
    primary_target: TrueFalseUnknown
    affinity_units: str
    affinity_median: float


@dataclass
class G2pData:
    inchikey: str
    g2pid: int
    name: str
    type: str
    approved: bool
    pubchem_id: Optional[int]
    interactions: List[G2pInteraction]


__all__ = ["G2pInteraction", "G2pData", "TrueFalseUnknown"]
