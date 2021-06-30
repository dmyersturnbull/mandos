"""
Common argument processing and arguments for Typer.
"""

from inspect import cleandoc
from pathlib import Path
from typing import Optional, TypeVar, Sequence, Union

import typer
from mandos.model.settings import MANDOS_SETTINGS

T = TypeVar("T", covariant=True)


class _Args:
    @staticmethod
    def _arg(doc: str, *names, default: Optional[T] = None, req: bool = False, **kwargs):
        kwargs = dict(
            help=cleandoc(doc),
            **kwargs,
            allow_dash=True,
        )
        return typer.Argument(default, **kwargs) if req else typer.Option(default, *names, **kwargs)

    @staticmethod
    def _path(
        doc: str, *names, default: Optional[str], f: bool, d: bool, out: bool, req: bool, **kwargs
    ):
        # if it's None, we're going to have a special default set afterward, so we'll explain it in the doc
        if out and default is None:
            kwargs = dict(show_default=True, **kwargs)
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
    def x(doc: str, *names, default: Optional[T] = None, **kwargs):
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


def _strip(s: str) -> str:
    return s.strip().strip("'").strip('"').strip()


class CommonArgs:
    @staticmethod
    def parse_taxon_id_or_name(taxon: Union[int, str]) -> Union[int, str]:
        if isinstance(taxon, str):
            return taxon
        elif isinstance(taxon, str) and taxon.isdigit():
            return int(taxon)
        raise ValueError(f"Taxon {taxon} must be an ID or name")

    @staticmethod
    def parse_taxon_id(taxon: Union[int, str]) -> int:
        try:
            return int(taxon)
        except ValueError:
            raise ValueError(f"Taxon {taxon} must be an exact ID") from None

    @staticmethod
    def parse_taxa(taxa: str) -> Sequence[Union[int, str]]:
        taxa = [_strip(t) for t in taxa.split(",")]
        return [CommonArgs.parse_taxon_id_or_name(t) for t in taxa]

    output_formats = r"""
        The filename extension must be one of: .feather; .snappy/.parquet;
        .csv, .tsv, .tab, .json (with optional .gz/.bz2/.zip/.xz);
        Feather (.feather) and Parquet (.snappy) are recommended.
        If only a filename suffix is provided, only sets the format and filename suffix.
        If no extension is provided, interprets that path as a directory and uses the default format (Feather).

        Will fail if the file exists, unless `--replace` is passed.
    """

    input_formats = r"""
        The filename extension must be one of: .feather; .snappy/.parquet;
        .csv, .tsv, .tab (with optional .gz/.bz2/.zip/.xz);
        Feather (.feather) and Parquet (.snappy) are recommended formats.
        (Some other formats, such as .json or .h5, may be permitted but are discouraged.)
    """

    file_input = Arg.in_file("The path to a file output by `:concat` or `:search`.", "input")

    compounds = Arg.in_file(
        """
        The path to the input file.
        One of:

          (A) *.txt, *.lines, or *.list (optionally with .gz/.zip/.xz/.bz2)), with one InChI Key per line;

          (B) A *.csv, *.tsv, *.tab file (or .gz/.zip/.xz/.bz2 variant) with a column called 'inchikey'; OR

          (C) An Arrow *.feather file or Parquet *.snappy file with a column called 'inchikey'
        """
    )

    dir_input = Arg.in_dir(
        rf"""
        The path to a directory containing files output from mandos search.

        {input_formats}
        Note that *all* matching files will be included.
        Provide ``--exclude`` if needed.
        """
    )

    to_single = Opt.out_file(
        rf"""
        The path to the output file.

        {output_formats}

        [default: <input-path>/{...}.{MANDOS_SETTINGS.default_table_suffix}.gz]
        """,
        "--to",
    )

    input_matrix: Path = Arg.in_file(
        rf"""
        The path to a similarity matrix file to write to.

        {input_formats}
        .txt/.txt.gz/etc. is assumed to be whitespace-delimited.
        TCompounds can be referenced by InChI Key or compound ID (matching what you provided for the search).
        The set of compounds here must exactly match the set of compounds in the input files.
        For Excel and text formats, the first row and the first column (header and index) indicate the compounds.

        Values must be floating-point.
        """
    )
    replace: bool = typer.Option(
        False, help="Replace output file(s) if they exist. See also: --skip"
    )

    taxa = Opt.val(
        r"""
        The IDs or names of UniProt taxa, comma-separated.
        Taxon names and common names can be used for vertebrate species (where available).

        This can have a significant effect on searches. See the docs for more info.

        [default: 7742] (Euteleostomi)
        """,
        "--taxa",
        "7742",
        show_default=False,
    )

    seed = Opt.val(r"A random seed (integer).", "--seed", default=0)

    n_samples = Opt.val(
        "Number of bootstrap samples (positive integer).",
        "--samples",
        min=1,
        default=2000,
    )

    exclude = Opt.val("A glob pattern matching input filenames to ignore.")

    verbose: bool = Opt.flag(
        r"Configure logger to output INFO (use ``--quiet`` for less info)",
        "-v",
        "--verbose",
    )

    quiet: bool = Opt.flag(
        r"Configure logger to output only ERROR (use ``--verbose`` for more info)",
        "-q",
        "--quiet",
    )

    in_cache: bool = Opt.flag(
        r"Do not download any data and fail if needed data is not cached.",
        hidden=True,
    )

    as_of: Optional[str] = Opt.val(
        f"""
        Restrict to data that was cached as of some date and time.
        This option can be useful for reproducibility.

        Note that this should imply that underlying data sources (such as of deposition or publication)
        are restricted by this datetime, but that is not checked.

        Examples:

            - --as-of 2021-10-11T14:12:13Z
            - --as-of 2021-10-11T14:12:13+14:00
            - --as-of 2021-10-11T14:12:13.496Z
            - --as-of "2021-10-11 14:12:13,496,915+14:00"
            - --as-of "2021-10-11 14:12:13-8:00 [America/Los_Angeles]"

        This is a subset of ISO 8601, represented as ``YYYY-mm-dd('T'|' '):hh:MM:ss(i)Z``.
        Precision must be nanosecond or less, and ``,`` and ``.`` are equivalent as a thousands separator.
        You can provide an IANA zone name in square brackets for context, but the offset is still required.
        """
    )

    log_path = Opt.out_path(
        r"""
        Also log to a file.
        The suffix can be .log, .log.gz, .log.zip, or .json, .json.gz, or .json.gz.
        You can prefix the path with :LEVEL: to control the level. For example, ``:INFO:out.log``
        """,
        "--log",
        show_default=True,
    )

    no_setup: bool = Opt.flag(
        r"Skip setup, such as configuring logging.",
        "--no-setup",
        hidden=True,
    )


cli = typer.Typer()


@cli.command()
def run(
    path: Path = CommonArgs.dir_input,
    x=CommonArgs.log_path,
):
    pass


if __name__ == "__main__":
    typer.run(run)


__all__ = ["CommonArgs", "Arg", "Opt"]
