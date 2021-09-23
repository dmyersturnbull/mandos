from pathlib import Path
from typing import Set, Sequence, Optional, Union, Tuple

from pocketutils.core.exceptions import PathExistsError
from regex import regex
from typeddfs import FileFormat

from mandos.model.utils.setup import logger
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.apis.chembl_support.chembl_activity import DataValidityComment
from mandos.model.apis.chembl_support.chembl_targets import TargetType
from mandos.model.apis.pubchem_support.pubchem_models import ClinicalTrialsGovUtils
from mandos.model.taxonomy import Taxonomy
from mandos.model.taxonomy_caches import TaxonomyFactories

DEF_SUFFIX = MANDOS_SETTINGS.default_table_suffix


class EntryUtils:
    """ """

    @classmethod
    def adjust_filename(cls, to: Optional[Path], default: Union[str, Path], replace: bool) -> Path:
        if to is None:
            path = Path(default)
        elif str(to).startswith("."):
            path = Path(default).with_suffix(str(to))
        elif str(to).startswith("*."):
            path = Path(default).with_suffix(str(to)[1:])
        elif to.is_dir() or to.suffix == "":
            path = to / default
        else:
            path = Path(to)
        if path.exists() and not replace:
            raise PathExistsError(f"File {path} already exists")
        elif replace:
            logger.info(f"Overwriting existing file {path}.")
        return path

    @classmethod
    def adjust_dir_name(cls, to: Optional[Path], default: Union[str, Path]) -> Tuple[Path, str]:
        out_dir = Path(default)
        suffix = DEF_SUFFIX
        if to is not None:
            pat = regex.compile(r"([^\*]*)(?:\*(\..+))", flags=regex.V1)
            m: regex.Match = pat.fullmatch(to)
            out_dir = default if m.group(1) == "" else m.group(1)
            suffix = DEF_SUFFIX if m.group(2) == "" else m.group(2)
            if out_dir.startswith("."):
                logger.warning(f"Writing to {out_dir} - was it meant as a suffix instead?")
            out_dir = Path(out_dir)
        if out_dir.exists() and not out_dir.is_dir():
            raise PathExistsError(f"Path {out_dir} already exists but is not a directory")
        FileFormat.from_suffix(suffix)  # make sure it's ok
        if out_dir.exists():
            n_files = len(list(out_dir.iterdir()))
            if n_files > 0:
                logger.warning(f"Directory {out_dir} is non-emtpy")
        return out_dir, suffix

    @staticmethod
    def split(st: str) -> Set[str]:
        return {s.strip() for s in st.split(",")}

    @staticmethod
    def get_taxa(taxa: Optional[str]) -> Sequence[Taxonomy]:
        if taxa is None:
            return []
        factory = TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path)
        return [factory.load(str(taxon).strip()) for taxon in taxa.split(",")]

    @staticmethod
    def get_trial_statuses(st: str) -> Set[str]:
        return ClinicalTrialsGovUtils.resolve_statuses(st)

    @staticmethod
    def get_target_types(st: str) -> Set[str]:
        return {s.name for s in TargetType.resolve(st)}

    @staticmethod
    def get_flags(st: str) -> Set[str]:
        return {s.name for s in DataValidityComment.resolve(st)}


__all__ = ["EntryUtils"]
