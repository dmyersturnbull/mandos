from __future__ import annotations
import os
from dataclasses import dataclass
from inspect import cleandoc
from pathlib import Path
from typing import (
    AbstractSet,
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import typer
from pocketutils.core.exceptions import PathExistsError, XTypeError, XValueError
from pocketutils.tools.path_tools import PathTools
from regex import regex
from typeddfs.df_errors import FilenameSuffixError

from mandos.model.apis.chembl_support.chembl_targets import TargetType
from mandos.model.apis.pubchem_support.pubchem_models import ClinicalTrialsGovUtils
from mandos.model.settings import SETTINGS, Globals
from mandos.model.taxonomy import Taxonomy
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.model.utils.setup import logger

T = TypeVar("T", covariant=True)


@dataclass(frozen=True, repr=True, order=True)
class ParsedTaxa:
    source: str
    allow: Sequence[Union[int, str]]
    forbid: Sequence[Union[int, str]]
    ancestors: Sequence[Union[int, str]]

    @classmethod
    def empty(cls) -> ParsedTaxa:
        return ParsedTaxa("", [], [], [])


class _Args:
    @staticmethod
    def _arg(doc: str, *names, default: Optional[T] = None, req: bool = False, **kwargs):
        kwargs = dict(
            help=cleandoc(doc),
            **kwargs,
            allow_dash=True,
        )
        if req:
            return typer.Argument(default, **kwargs)
        else:
            return typer.Option(default, *names, **kwargs)

    @staticmethod
    def _path(
        doc: str, *names, default: Optional[str], f: bool, d: bool, out: bool, req: bool, **kwargs
    ):
        # if it's None, we're going to have a special default set afterward, so we'll explain it in the doc
        if out and default is None:
            kwargs = dict(show_default=False, **kwargs)
        kwargs = {
            **dict(
                exists=not out,
                dir_okay=d,
                file_okay=f,
                readable=out,
                writable=not out,
            ),
            **kwargs,
        }
        return _Args._arg(doc, *names, default=default, req=req, **kwargs)


class Arg(_Args):
    @staticmethod
    def out_file(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=False, out=True, req=True, **kwargs
        )

    @staticmethod
    def out_dir(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=True, out=True, req=True, **kwargs
        )

    @staticmethod
    def out_path(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=True, out=False, req=True, **kwargs
        )

    @staticmethod
    def in_file(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=False, out=False, req=True, **kwargs
        )

    @staticmethod
    def in_dir(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=False, d=True, out=False, req=True, **kwargs
        )

    @staticmethod
    def in_path(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=True, out=False, req=True, **kwargs
        )

    @staticmethod
    def val(doc: str, *names, default: Optional[T] = None, **kwargs):
        return _Args._arg(doc, *names, default=default, req=True, **kwargs)


class Opt(_Args):
    @staticmethod
    def out_file(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=False, out=True, req=False, **kwargs
        )

    @staticmethod
    def out_dir(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=True, out=True, req=False, **kwargs
        )

    @staticmethod
    def out_path(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc,
            *names,
            default=default,
            f=True,
            d=True,
            out=False,
            req=False,
            exists=False,
            **kwargs,
        )

    @staticmethod
    def in_file(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=True, d=False, out=False, req=False, **kwargs
        )

    @staticmethod
    def in_dir(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc, *names, default=default, f=False, d=True, out=False, req=False, **kwargs
        )

    @staticmethod
    def in_path(doc: str, *names, default: Optional[str] = None, **kwargs):
        return _Args._path(
            doc,
            *names,
            default=default,
            f=True,
            d=True,
            out=False,
            req=False,
            exists=False,
            **kwargs,
        )

    @staticmethod
    def val(doc: str, *names, default: Optional[T] = None, **kwargs):
        return _Args._arg(doc, *names, default=default, req=False, **kwargs)

    @staticmethod
    def flag(doc: str, *names, **kwargs):
        return _Args._arg(doc, *names, default=False, req=False, **kwargs)


class ArgUtils:
    @classmethod
    def definition_bullets(cls, dct: Mapping[Any, Any], colon: str = ": ", indent: int = 12) -> str:
        joiner = os.linesep * 2 + " " * indent
        jesus = [f" - {k}{colon}{v}" for k, v in dct.items()]
        return joiner.join(jesus)

    @classmethod
    def definition_list(cls, dct: Mapping[Any, Any], colon: str = ": ", sep: str = "; ") -> str:
        jesus = [f"{k}{colon}{v}" for k, v in dct.items()]
        return sep.join(jesus)

    @classmethod
    def list(
        cls,
        lst: Iterable[Any],
        *,
        attr: Union[None, str, Callable[[Any], Any]] = None,
        sep: str = ", ",
    ) -> str:
        x = []
        for v in lst:
            if attr is None and hasattr(v, "name"):
                x += [v.name]
            elif attr is None:
                x += [str(v)]
            elif isinstance(attr, str):
                x += [str(getattr(v, attr))]
            else:
                x += [str(attr(v))]
        return sep.join(x)

    @classmethod
    def get_taxonomy(
        cls,
        taxa: Optional[str],
        *,
        local_only: bool = False,
        allow_forbid: bool = True,
    ) -> Optional[Taxonomy]:
        if taxa is None or len(taxa) == 0:
            return None
        parsed = cls.parse_taxa(taxa, allow_forbid=allow_forbid)
        return TaxonomyFactories.get_smart_taxonomy(
            allow=parsed.allow,
            forbid=parsed.forbid,
            ancestors=parsed.ancestors,
            local_only=local_only,
        )

    @classmethod
    def parse_taxa(
        cls,
        taxa: Optional[str],
        *,
        allow_forbid: bool = True,
    ) -> ParsedTaxa:
        if taxa is None or taxa == "":
            return ParsedTaxa.empty()
        ancestors = f"{Globals.cellular_taxon},{Globals.viral_taxon}"
        if ":" in taxa:
            ancestors = taxa.split(":", 1)[1]
            taxa = taxa.split(":", 1)[0]
        taxa_objs = [t.strip() for t in taxa.split(",") if len(t.strip()) > 0]
        allow = [t.strip().lstrip("+") for t in taxa_objs if not t.startswith("-")]
        forbid = [t.strip().lstrip("-") for t in taxa_objs if t.startswith("-")]
        ancestors = [t.strip() for t in ancestors.split(",")]
        if not allow_forbid and len(forbid) > 0:
            raise XValueError(f"Cannot use '-' in {taxa}")
        return ParsedTaxa(
            source=taxa,
            allow=[ArgUtils.parse_taxon(t, id_only=False) for t in allow],
            forbid=[ArgUtils.parse_taxon(t, id_only=False) for t in forbid],
            ancestors=[ArgUtils.parse_taxon(t, id_only=True) for t in ancestors],
        )

    @classmethod
    def parse_taxa_ids(cls, taxa: str) -> Sequence[int]:
        """
        Does not allow negatives.
        """
        if taxa is None or taxa == "":
            return []
        taxa = [t.strip() for t in taxa.split(",") if len(t.strip()) > 0]
        return [ArgUtils.parse_taxon(t, id_only=True) for t in taxa]

    @classmethod
    def parse_taxon(cls, taxon: Union[int, str], *, id_only: bool = False) -> Union[int, str]:
        std = cls._get_std_taxon(taxon)
        if isinstance(taxon, str) and taxon in std:
            return std
        if isinstance(taxon, str) and not id_only:
            return taxon
        elif isinstance(taxon, str) and taxon.isdigit():
            return int(taxon)
        if id_only:
            raise XTypeError(f"Taxon {taxon} must be an ID")
        raise XTypeError(f"Taxon {taxon} must be an ID or name")

    @classmethod
    def _get_std_taxon(cls, taxa: str) -> str:
        x = dict(
            vertebrata=Globals.vertebrata,
            vertebrate=Globals.vertebrata,
            vertebrates=Globals.vertebrata,
            cellular=Globals.cellular_taxon,
            cell=Globals.cellular_taxon,
            cells=Globals.cellular_taxon,
            viral=Globals.viral_taxon,
            virus=Globals.viral_taxon,
            viruses=Globals.viral_taxon,
            all=f"{Globals.cellular_taxon},{Globals.viral_taxon}",
        ).get(taxa)
        return taxa if x is None else str(x)

    @staticmethod
    def get_trial_statuses(st: str) -> Set[str]:
        return ClinicalTrialsGovUtils.resolve_statuses(st)

    @staticmethod
    def get_target_types(st: str) -> Set[str]:
        return {s.name for s in TargetType.resolve(st)}


class EntryUtils:
    @classmethod
    def adjust_filename(
        cls,
        to: Optional[Path],
        default: Union[str, Path],
        replace: bool,
        *,
        suffixes: Union[None, AbstractSet[str], Callable[[Union[Path, str]], Any]] = None,
    ) -> Path:
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
        path = Path(path)
        if os.name == "nt" and SETTINGS.sanitize_paths:
            new_path = PathTools.sanitize_path_nodes(path._parts, is_file=True)
            if new_path.resolve() != path.resolve():
                logger.warning(f"Sanitized filename {path} → {new_path}")
                path = new_path
        if (
            path.exists()
            and not path.is_file()
            and not path.is_socket()
            and not path.is_char_device()
        ):
            raise PathExistsError(f"Path {path} exists and is not a file")
        if path.exists() and not replace:
            raise PathExistsError(f"File {path} already exists")
        cls._check_suffix(path.suffix, suffixes)
        if path.exists() and replace:
            logger.info(f"Overwriting existing file {path}")
        return path

    @classmethod
    def adjust_dir_name(
        cls,
        to: Optional[Path],
        default: Union[str, Path],
        *,
        suffixes: Union[None, AbstractSet[str], Callable[[Union[Path, str]], Any]] = None,
    ) -> Tuple[Path, str]:
        out_dir = Path(default)
        suffix = SETTINGS.table_suffix
        if to is not None:
            pat = regex.compile(r"([^\*]*)(?:\*(\..+))", flags=regex.V1)
            m: regex.Match = pat.fullmatch(to)
            out_dir = default if m.group(1) == "" else m.group(1)
            suffix = SETTINGS.table_suffix if m.group(2) == "" else m.group(2)
            if out_dir.startswith("."):
                logger.warning(f"Writing to {out_dir} — was it meant as a suffix instead?")
            out_dir = Path(out_dir)
        if os.name == "nt" and SETTINGS.sanitize_paths:
            new_dir = PathTools.sanitize_path_nodes(out_dir._parts, is_file=True)
            if new_dir.resolve() != out_dir.resolve():
                logger.warning(f"Sanitized directory {out_dir} → {new_dir}")
                out_dir = new_dir
        if out_dir.exists() and not out_dir.is_dir():
            raise PathExistsError(f"Path {out_dir} already exists but and is not a directory")
        cls._check_suffix(suffix, suffixes)
        if out_dir.exists():
            n_files = len(list(out_dir.iterdir()))
            if n_files > 0:
                logger.debug(f"Directory {out_dir} is non-emtpy")
        return out_dir, suffix

    @classmethod
    def _check_suffix(cls, suffix, suffixes):
        if suffixes is not None and callable(suffixes):
            try:
                suffixes(suffix)  # make sure it's ok
            except FilenameSuffixError:
                raise XValueError(f"Unsupported file format {suffix}")
        elif suffixes is not None:
            if suffix not in suffixes:
                raise XValueError(f"Unsupported file format {suffix}")


__all__ = ["Arg", "Opt", "ArgUtils", "EntryUtils"]
