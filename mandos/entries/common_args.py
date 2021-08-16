"""
Common argument processing and arguments for Typer.
"""
import enum
import os
from inspect import cleandoc
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, TypeVar, Union, List

import typer
from typeddfs.utils import Utils as TypedDfsUtils

from mandos.model.utils import CleverEnum
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
    def definition_bullets(dct: Mapping[Any, Any], colon: str = ": ", indent: int = 12) -> str:
        joiner = os.linesep * 2 + " " * indent
        jesus = [f" - {k}{colon}{v}" for k, v in dct.items()]
        return joiner.join(jesus)

    @staticmethod
    def definition_list(dct: Mapping[Any, Any], colon: str = ": ", sep: str = "; ") -> str:
        jesus = [f"{k}{colon}{v}" for k, v in dct.items()]
        return sep.join(jesus)

    @staticmethod
    def list(
        lst: Iterable[Any], attr: Union[None, str, Callable[[Any], Any]] = None, sep: str = "; "
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
        The filename extension must be one of: .feather; .snappy/.parquet; or
        .csv, .tsv, .tab (with optional .gz/.bz2/.zip/.xz).
        Feather (.feather) and Parquet (.snappy) are recommended.
        If only a filename suffix is provided, only sets the format and suffix.
        If no suffix is provided, interprets that path as a directory and uses Feather.
        Will fail if the file exists, unless `--replace` is passed.
    """

    input_formats = r"""
        The filename extension must be one of: .feather; .snappy/.parquet;
        .csv, .tsv, .tab (with optional .gz/.bz2/.zip/.xz);
        Feather (.feather) and Parquet (.snappy) are recommended.
        (.json and .h5 may be accepted but are discouraged.)
    """

    doc_output = Arg.in_file(
        r"""
        The path to write command documentation to.

        The filename can end with .txt with optional compression (e.g. .txt.gz)
        for formatted text output alongside --format.

        Can can also use any table format: .feather; .snappy/.parquet;
        or .csv, .tsv, .tab, .json, .flexwf (with optional .gz/.bz2/.zip/.xz).

        [default: "commands-level<level>.txt"]
        """
    )

    doc_style = Arg.x(
        rf"""
        The format for formatted text output.

        This is ignored if --to is not a .txt file (or .txt.gz, etc.).
        The choices are: {", ".join(TypedDfsUtils.table_formats())}.
        """,
        default="fancy_grid",
    )

    file_input = Arg.in_file(
        r"""
        The path to a file output by ``:concat`` or ``:search``.
        """
    )

    alpha_input: Path = Opt.in_file(
        rf"""
            Path to a table containing scores.

            Required columns are 'inchikey', 'score_name', and 'score_value'.

            The InChI Keys must match those provided for the search.
            Each score must start with either 'score_' or 'is_'.

            {input_formats}
            """
    )

    on: bool = Opt.val(
        r"""
            Determines whether the resulting rows mark single predicate/object pairs,
            or sets of pairs.

            **If "choose"**, decides whether to use intersection or union based on the search type.
            For example, ``chembl:mechanism`` use the intersection,
            while most others will use the union.

            **If "intersection"**, each compound will contribute to a single row
            for its associated set of pairs.
            For example, a compound annotated for ``increase dopamine`` and ``decrease serotonin``
            increment the count for a single row:
            object ``["dopamine", "serotonin"]`` and predicate ``["increase", "decrease"]``.
            (Double quotes will be escaped.)

            **If "union"**, each compound will contribute to one row per associated pair.
            In the above example, the compound will increment the counts
            of two rows: object=``dopamine`` / predicate=``increase``
            and ``object=serotonin`` and predicate=``decrease``.

            In general, this flag is useful for variables in which
            a *set of pairs* best is needed to describe a compound,
            and there are likely to be relatively few unique predicate/object pairs.
        """
    )

    ci = Opt.val(
        f"""
        The upper side of the confidence interval, as a percentage.
        """,
        default=95.0,
    )

    plot_to: Optional[Path] = Opt.out_file(
        r"""
            Path to an output directory for figures.

            All plots will be vectorized and written as PDF.

            [default: <input-dir>]
            """
    )

    project_to: Optional[Path] = Opt.out_file(
        r"""
            Path to the output table.

            The columns will include 'x' and 'y'.

            [default: <path>-<algorithm>...],
        """
    )

    project_input: Optional[Path] = Opt.in_file(
        rf"""
            Path to data from ``:calc:umap`` or a similar command.
        """
    )

    plot_kind: str = Opt.val(
        r"""
        The type of plot: bar, box, violin, or swarm.

        - 'fold': Two-layered bar plot of 'true' (opaque) against all (translucent).
          E.g.: 'is_hit' in deep blue against total=is_hit+not_hit in a 50%-opacity blue.
          True is defined as != 0 for numbers and != '' for strings.

        - 'bar': Bar plot with error bars for CI

        - 'box': Box plot (always uses standard deviation)

        - 'violin': Violin plot. Bandwidth determined by Scott's algorithm.
          No quartiles or std shown, and data are truncated at the range of the observations.

        - 'swarm' Vertical scatter plot
        """,
        "--type",
        default="choose",
    )

    style_for_compounds: Optional[Path] = Opt.in_file(
        r"""
        Path to a table mapping compounds to colors and markers.

        If this is set, ``--colors`` and ``--markers`` will refer to columns in this file.
        Otherwise, they will refer to columns in the input.
        Should contain a column called "inchikey", along with 0 or more additional columns.
        See ``--colors`` and ``--markers`` for info on the formatting.
        """
    )

    style_for_pairs: Optional[Path] = Opt.in_file(
        r"""
        Path to a table mapping predicate/object pairs to colors and markers.

        NOTE: This is currently not supported when using predicate/object pair intersection.

        If this is set, ``--colors`` and ``--markers`` will refer to columns in this file.
        Otherwise, they will refer to columns in the input.
        Should contain columns "key", "predicate", and "object", along with 0 or more additional columns.
        The "key" refers to the search key specified in ``:search``.
        Any null (empty-string) value will be taken to mean any/all.
        (The main use is to easily collapse over all predicates.)
        See ``--colors`` and ``--markers`` for info on the formatting.
        """
    )

    style_for_psi: Optional[Path] = Opt.in_file(
        r"""
        Path to a table mapping each psi variable name to a color and marker.

        If this is set, ``--colors`` and ``--markers`` will refer to columns in this file.
        Otherwise, they will refer to columns in the input.
        Should contain a "psi" column, along with 0 or more additional columns.
        See ``--colors`` and ``--markers`` for info on the formatting.
        """
    )

    color_col: Optional[Path] = Opt.val(
        rf"""
        The column to use for colors.

        If not specified, Mandos will use one color, unless the plot requires more.
        If required, a semi-arbitrary column will be chosen.

        If the values are _ ... mandos uses _.

        - matplotlib-recognized (e.g. #ff0022, 'red', or '(255,0,0)') ... them literally.

        - General strings ... a categorical palette.

        - Booleans (or 0/1) ... a bright color and a dark color.

        - Numbers of the same sign (or 0) ...  a sequential palette.

        - Both positive and negative numbers ... a divergent palette.
        """,
        "--colors",
    )

    marker_col: Optional[Path] = Opt.val(
        rf"""
        The column to use for markers.

        If not specified, Mandos will use one marker shape, unless the plot requires more.
        If required, a semi-arbitrary column will be chosen.

        If the values are matplotlib-recognized (e.g. ``:`` or ``o``), mandos uses those.
        Otherwise, markers are chosen from the available set and mapped to the distinct values.
        """,
        "--markers",
    )

    alpha_to: Optional[Path] = Opt.out_file(
        rf"""
            Path to write enrichment info.

            {output_formats}

            One row will be included per predicate/object pair (or list of them), per bootstrap sample.
            Rows with a null bootstrap sample are not sub-sampled.
            Columns will correspond to the columns you provided.

            [default: <path>-correlation-<scores.filename>{MANDOS_SETTINGS.default_table_suffix}]
            """
    )

    id_table_to: Path = Opt.out_path(
        rf"""
            A table of compounds and their database IDs will be written here.

            {output_formats}

            [default: <path>-ids-<start-time>.{MANDOS_SETTINGS.default_table_suffix}]
            """
    )

    compounds = Arg.in_file(
        rf"""
        The path to the file listing compounds.

        Must contain a column called 'inchikey'. If provided, a 'compound_id' column
        will be copied in the results to facilitate lookups.

        Some searches and commands require a full structure via either "inchi" or "smiles"
        as a column. These will only be used as needed.

        {input_formats}
        """
    )

    compounds_to_fill = Arg.in_file(
        rf"""
        The path to the file listing compounds by various IDs.

        Can use columns called 'inchikey', 'chembl_id', and 'pubchem_id'.
        Other columns are permitted but will not be used.

        {input_formats}
        """,
    )

    input_dir = Arg.in_dir(
        rf"""
        Directory containing results from a mandos search.

        {input_formats}
        """
    )

    to_single = Opt.out_file(
        rf"""
        Output file containing annotations.

        {output_formats}

        [default: <input-path>/{...}.{MANDOS_SETTINGS.default_table_suffix}]
        """
    )

    misc_out_dir = Opt.val(
        rf"""
        Output directory.

        Must be empty unless ``--replace`` is set

        [default: same as input directory]
        """,
    )

    out_dir = Opt.val(
        rf"""
        Choose the output directory.

        You can set alongside ``--to``.
        If ``--to`` is set to a relative path, this value is prepended.

        [default: none]
        """,
        "--dir",
    )

    input_matrix: Path = Arg.in_file(
        rf"""
        The path to a file with compound/compound similarity matrices.

        {input_formats}

        The matrix is "long-form" so that multiple matrices can be included.
        Columns are "inchikey_1", "inchikey_2", "key", and "type".
        The key is the specific similarity matrix; it is usually the search_key
        for psi matrices (computed from annotations from :search), and
        a user-provided value for phi matrices (typically of phenotypic similarity).
        The "type" column should contain either "phi" or "psi" accordingly.
        """
    )

    output_matrix: Path = Arg.out_file(
        rf"""
        The path to a file with compound/compound similarity matrices.

        The matrix is "long-form" so that multiple matrices can be included.

        You can provide just a filename suffix to change the format and suffix
        but otherwise use the default path.

        [default: inferred from input path(s)]
        """,
    )

    input_matrix_short_form = Arg.in_file(
        rf"""
        The path to a file with a compound/compound similarity matrix.

        {input_formats}

        The matrix is "short-form": the first row and first column list the InChI Keys.
        The table must be symmetric (the rows and columns listed in the same order).
        """
    )

    var_type: str = Opt.val(
        r"""
        Either "phi" or "psi".
        """,
        default="phi",
        hidden=True,
    )

    input_correlation: Path = Arg.in_file(
        rf"""
        The path to a file from ``:calc:score``.

        {input_formats}
        """
    )

    replace: bool = Opt.flag(
        r"Replace output file(s) if they exist. See also: --skip.", "--replace"
    )

    taxa = Opt.val(
        r"""
        The IDs of UniProt taxa, comma-separated.

        This can have a significant effect on searches. See the docs.
        Taxon scientific names, common names, and mnemonics can be used for vertebrate species.
        To find more, explore the hierarchy under:

        - https://www.uniprot.org/taxonomy/131567 (cellular species)

        - https://www.uniprot.org/taxonomy/10239 (viral species)

        [default: 7742] (Euteleostomi)
        """,
        "--taxa",
        "7742",
        show_default=False,
    )

    seed = Opt.val(r"Random seed (integer).", default=0)

    boot = Opt.val(
        r"""
        Also generate results for <b> bootstrapped samples.

        Number of bootstrap samples (positive integer).

        If set, will still include the non-bootstrapped results (sample=0 in the output).
        """,
        min=1,
        max=1000000,
        default=0,
    )

    exclude = Opt.val(
        r"""
        Regex for input filenames to ignore.

        The regular expressions variant is from Python's 're' library.
        """
    )

    verbose: bool = Opt.flag(
        r"""
        Show more logging output.

        Configures the logger to output INFO (use ``--quiet`` for less info).
        """,
        "-v",
        "--verbose",
    )

    quiet: bool = Opt.flag(
        r"""
        Show less logging output.

        Configures logger to output only ERROR (use ``--verbose`` for more info)
        """,
        "-q",
        "--quiet",
    )

    yes: bool = Opt.flag(
        r"""
        Answer yes to all prompts (non-interactive).
        """,
    )

    in_cache: bool = Opt.flag(
        r"""
        Do not download any data, and fail if needed data is not cached.
        """,
        "--in-cache",
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

            - --as-of "2021-10-11 14:12:13,496,915+14:00"

            - --as-of "2021-10-11 14:12:13-8:00 [America/Los_Angeles]"

        The supported syntax is ``YYYY-mm-dd'T':hh:MM:ss(iii[.iii][.iii)Z``.
        You can use a space instead of 'T' and ',' as a thousands separator.
        A UTC offset is required, even with an IANA zone in brackets.
        """
    )

    log_path = Opt.out_path(
        r"""
        Log to a file as well as stderr.

        The suffix can be .log, .log.gz, .log.zip, .json, .json.gz, or .json.gz.
        Prefix the path with :LEVEL: to control the level for this file (e.g. ``:INFO:out.log``).
        """,
    )

    no_setup: bool = Opt.flag(
        r"Skip setup, such as configuring logging.",
        "--no-setup",
        hidden=True,
    )


cli = typer.Typer()


@cli.command()
def run(
    path: Path = CommonArgs.input_dir,
    x=CommonArgs.log_path,
):
    pass


if __name__ == "__main__":
    typer.run(run)


__all__ = ["CommonArgs", "Arg", "Opt"]
