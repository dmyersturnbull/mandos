from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Optional, Sequence, Set

from chembl_webresource_client.settings import Settings as ChemblSettings
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.targets import TargetType

instance = ChemblSettings.Instance()
_IS_IN_CI = "IS_IN_CI" in os.environ
if _IS_IN_CI:
    DEFAULT_MANDOS_CACHE = (
        Path(__file__).parent.parent.parent / "tests" / "resources" / ".mandos-cache"
    )
else:
    DEFAULT_MANDOS_CACHE = Path(
        {k.lower(): v for k, v in os.environ.items()}.get("MANDOS_HOME", Path.home() / ".mandos")
    )

DEFAULT_CHEMBL_CACHE = DEFAULT_MANDOS_CACHE / "chembl"
DEFAULT_TAXONOMY_CACHE = DEFAULT_MANDOS_CACHE / "taxonomy"
DEFAULT_BAD_FLAGS = [
    "potential missing data",
    "potential transcription error",
    "outside typical range",
]
logger = logging.getLogger("mandos")


@dataclass(frozen=True, repr=True)
class Settings:
    """"""

    is_testing: bool
    traversal_strategy: Optional[str]
    require_taxon: bool
    taxon: int
    allowed_assay_types: FrozenSet[str]
    allowed_relations: FrozenSet[str]
    allowed_target_types: FrozenSet[str]
    banned_flags: FrozenSet[str]
    require_pchembl: bool
    min_pchembl: float
    require_confidence_score: bool
    min_confidence_score: int
    min_phase: int
    random_seed: int
    n_bootstrap_samples: int
    cache_path: Path
    n_retries: int
    fast_save: bool
    timeout_sec: int
    use_pubchem_parent: bool
    min_query_delay: float
    max_query_delay: float
    tanimoto_vals: Sequence[float]
    unicode_ranges: Path
    stop_words: Path
    convert_greek: bool

    @property
    def chembl_cache_path(self) -> Path:
        return self.cache_path / "chembl"

    @property
    def pubchem_cache_path(self) -> Path:
        return self.cache_path

    @classmethod
    def load(cls, data: NestedDotDict) -> Settings:
        #  117571
        mandos_home = data.get_as("mandos.cache_path", Path, DEFAULT_MANDOS_CACHE)
        default_target_types = [s.name for s in TargetType.all_types()]
        return Settings(
            is_testing=data.get_as("is_testing", bool, False),
            cache_path=mandos_home,
            random_seed=data.get_as("mandos.random_seed", int, 0),
            traversal_strategy=data.get_as("mandos.chembl.target.traversal_strategy", str, None),
            allowed_target_types=frozenset(
                data.get_list_as("mandos.chembl.target.allowed_types", str, default_target_types)
            ),
            require_taxon=data.get_as("mandos.chembl.target.require_taxon", bool, True),
            taxon=data.get_as("mandos.chembl.target.taxon", int, 7742),
            require_confidence_score=data.get_as(
                "mandos.chembl.target.require_confidence_score", bool, True
            ),
            allowed_assay_types=frozenset(
                data.get_list_as("mandos.chembl.activity.allowed_assay_types", str, ["B"])
            ),
            min_confidence_score=data.get_as(
                "mandos.chembl.activity.min_target_confidence_score", int, 4
            ),
            allowed_relations=frozenset(
                data.get_list_as("mandos.chembl.activity.allowed_relations", str, ["<", "<=", "="])
            ),
            require_pchembl=data.get_as("mandos.chembl.activity.require_pchembl", bool, True),
            min_pchembl=data.get_as("mandos.chembl.activity.min_pchembl", float, 6.0),
            banned_flags=frozenset(
                data.get_list_as("mandos.chembl.target.disallowed_flags", str, DEFAULT_BAD_FLAGS)
            ),
            min_phase=data.get_as("mandos.chembl.trial.min_phase", int, 3),
            min_query_delay=data.get_as("mandos.pubchem.query_delay_sec_min", float, 0.25),
            max_query_delay=data.get_as("mandos.pubchem.query_delay_sec_min", float, 0.25),
            use_pubchem_parent=data.get_as("mandos.pubchem.use_parent_molecule", bool, True),
            tanimoto_vals=data.get_list_as(
                "mandos.pubchem.similarity_tanimoto_values", float, [0.9]
            ),
            unicode_ranges=data.get_as("mandos.nlp.unicode_range_file", Path, None),
            stop_words=data.get_as("mandos.nlp.stop_word_file", Path, None),
            convert_greek=data.get_as("mandos.nlp.convert_greek", bool, True),
            n_bootstrap_samples=data.get_as("mandos.correlation.n_bootstrap_samples", int, 10000),
            n_retries=data.get_as("chembl.n_retries", int, 1),
            fast_save=data.get_as("chembl.fast_save", bool, True),
            timeout_sec=data.get_as("chembl.timeout_sec", int, 1),
        )

    @property
    def taxonomy_cache_path(self) -> Path:
        return self.cache_path / "taxonomy"

    def set(self):
        """

        Returns:

        """
        instance.CACHING = True
        if not _IS_IN_CI:  # not sure if this is needed
            instance.CACHE_NAME = str(self.chembl_cache_path)
            logger.info(f"Setting ChEMBL cache to {self.chembl_cache_path}")
        instance.TOTAL_RETRIES = self.n_retries
        instance.FAST_SAVE = self.fast_save
        instance.TIMEOUT = self.timeout_sec


__all__ = ["Settings", "DEFAULT_MANDOS_CACHE", "DEFAULT_CHEMBL_CACHE", "DEFAULT_TAXONOMY_CACHE"]
