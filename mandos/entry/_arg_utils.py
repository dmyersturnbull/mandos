import enum
import os
from inspect import cleandoc
from typing import Optional, Iterable, Any, Mapping, Union, Callable, Sequence, Type, TypeVar

import typer
from pocketutils.core.exceptions import BadCommandError, XValueError, XTypeError
from typeddfs import TypedDf


T = TypeVar("T", covariant=True)


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
    def df_description(cls, tdf: Type[TypedDf]) -> str:
        req = tdf.get_typing().required_columns
        res = [*tdf.get_typing().reserved_index_names, *tdf.get_typing().reserved_columns]
        line1 = "Required columns: " + ", ".join(req)
        line2 = "Optional columns: " + ", ".join(res)
        return line1 + "\n\n" + line2

    @classmethod
    def list(
        cls,
        lst: Iterable[Any],
        attr: Union[None, str, Callable[[Any], Any]] = None,
        sep: str = "; ",
    ) -> str:
        x = []
        for v in lst:
            if attr is None and isinstance(v, enum.Enum):
                x += [v.name]
            elif attr is None:
                x += [str(v)]
            elif isinstance(attr, str):
                x += [str(getattr(v, attr))]
            else:
                x += [str(attr(v))]
        return sep.join(x)

    @classmethod
    def parse_taxon_id_or_name(cls, taxon: Union[int, str]) -> Union[int, str]:
        if isinstance(taxon, str):
            return taxon
        elif isinstance(taxon, str) and taxon.isdigit():
            return int(taxon)
        raise XTypeError(f"Taxon {taxon} must be an ID or name")

    @classmethod
    def parse_taxon_id(cls, taxon: Union[int, str]) -> int:
        try:
            return int(taxon)
        except ValueError:
            raise XTypeError(f"Taxon {taxon} must be an exact ID") from None

    @classmethod
    def parse_taxa(cls, taxa: str) -> Sequence[Union[int, str]]:
        taxa = [t.strip() for t in taxa.split(",")]
        return [ArgUtils.parse_taxon_id_or_name(t) for t in taxa]


__all__ = ["Arg", "Opt", "ArgUtils"]
