from pathlib import Path
from typing import Sequence

import decorateme
import pandas as pd
import regex
from pocketutils.core.exceptions import ParsingError
from typeddfs import TypedDfs

from mandos.model.utils.setup import MandosResources, logger


def _patterns(self: pd.DataFrame) -> Sequence[str]:
    return self[self.columns[0]].values.tolist()


def _targets(self: pd.DataFrame) -> Sequence[str]:
    return self.columns[1:].values.tolist()


def _get(self: pd.DataFrame, s: str) -> Sequence[str]:
    for irow, pattern in enumerate(self[self.columns[0]].values):
        try:
            match: regex.Match = pattern.fullmatch(s)
        except AttributeError:
            raise ParsingError(f"Failed on regex {pattern}") from None
        if match is not None:
            return [pattern.sub(t, s.strip()) for t in self.T[irow] if isinstance(t, str)]
    return s


_doc = r"""
A list of regex patterns and replacements.
The first column is the pattern, and the next n columns are the targets.
Has an important function, ``MappingFrame.get``, describe below.
These DataFrames are used in a few places to clean up, simplify, or otherwise process
predicate and object names.

Example:

    For the input string "cyp450 2A3", consider we have these two rows:
    row 1: ``['^Juggle protein [xy]', 'Juggle \1', 'J\1']``
    row 2: ``['^CYP *450 (\d+)[A-Z]\d*$', 'Cytochrome P450 \1', 'CYP\1']``
    First, we try to match against the first pattern. It doesn't match, so we try the next.
    This one does match our input string, so we return ``["Cytochrome P450 2", "CYP2"]``.
    The first returned element (here "Cytochrome P450 2"), is considered the primary,
    while the second are -- for most usages -- considered optional extras.
"""

MappingDf = (
    TypedDfs.typed("MappingDf")
    .doc(_doc)
    .add_methods(targets=_targets, patterns=_patterns, get=_get)
    .post(lambda dfx: dfx.astype(str))
    .secure()
).build()


@decorateme.auto_repr_str()
class _Compiler:
    """
    Compiles multiple regex patterns, providing nice error messages.
    All patterns are global (i.e. ^ and $ are affixed) and case-insensitive.
    """

    def __init__(self):
        self._i = 0

    def compile(self, s: str) -> regex.Pattern:
        self._i += 1  # header is the first
        try:
            return regex.compile("^" + s.strip() + "$", flags=regex.V1 | regex.IGNORECASE)
        except regex.error:
            raise ParsingError(f"Failed to parse '{s}' on row {self._i}") from None


@decorateme.auto_repr_str()
class Mappings:
    """
    Creates MappingDfs.
    See that documentation.
    """

    @classmethod
    def from_resource(cls, name: str) -> MappingDf:
        path = MandosResources.a_file("mappings", name)
        return cls.from_path(path)

    @classmethod
    def from_path(cls, path: Path) -> MappingDf:
        """
        Reads a mapping from a CSV-like file or ``.regexes`` file.
        Feather and Parquet are fine, too.
        The ``.regexes`` suffix is a simple extension of CSV that uses ``|||`` as the delimiter.
        and ignores empty lines and lines beginning with ``#``.
        It's just nice for easily editing in a text editor.
        """
        df = MappingDf.read_file(path)
        compiler = _Compiler()
        df[df.columns[0]] = df[df.columns[0]].map(compiler.compile)
        logger.info(f"Read mapping with {len(df)} items from {path}")
        return df


__all__ = ["MappingDf", "Mappings"]
