import abc
from pathlib import Path
from typing import Generic, Mapping, Optional, Type, TypeVar, Union

import typer
from pocketutils.tools.reflection_tools import ReflectionTools
from typer.models import OptionInfo

from mandos import logger
from mandos.entry.tools.searchers import InputCompoundsDf, Searcher
from mandos.entry.utils._arg_utils import EntryUtils
from mandos.model.searches import Search
from mandos.model.settings import SETTINGS
from mandos.model.utils import MANDOS_SETUP

S = TypeVar("S", bound=Search, covariant=True)


class Entry(Generic[S], metaclass=abc.ABCMeta):
    @classmethod
    def cmd(cls) -> str:
        key = cls._get_default_key()
        if isinstance(key, typer.models.OptionInfo):
            key = key.default
        if key is None or not isinstance(key, str):
            raise AssertionError(f"Key for {cls.__name__} is {key}")
        return key

    @classmethod
    def describe(cls) -> str:
        lines = [line.strip() for line in cls.run.__doc__.splitlines() if line.strip() != ""]
        return lines[0]

    @classmethod
    def run(cls, path: Path, **params) -> None:
        raise NotImplementedError()

    @classmethod
    def get_search_type(cls) -> Type[S]:
        # noinspection PyTypeChecker
        return ReflectionTools.get_generic_arg(cls, Search)

    # noinspection PyUnusedLocal
    @classmethod
    def test(cls, path: Path, **params) -> None:
        cls.run(path, **{**params, **dict(check=True, log=None, stderr="ERROR")})

    @classmethod
    def _run(
        cls,
        built: S,
        path: Path,
        to: Optional[Path],
        replace: bool,
        proceed: bool,
        check: bool,
        log: Optional[Path],
        level: str,
    ) -> Searcher:
        MANDOS_SETUP(log, level)
        default_to = path.parent / (built.key + SETTINGS.table_suffix)
        # keep quiet -- we'll log in Searcher
        to = EntryUtils.adjust_filename(
            to, default=default_to, replace=replace or proceed, quiet=True
        )
        input_df = InputCompoundsDf.read_file(path)
        logger.info(f"Read {len(input_df)} input compounds")
        searcher = Searcher(built, input_df, to, restart=replace, proceed=proceed)
        logger.notice(f"Searching {built.key} [{built.search_class}] on {path}")
        if not check:
            searcher.search()
            logger.notice(f"Done! Wrote to {to}")
        return searcher

    @classmethod
    def default_param_values(cls) -> Mapping[str, Union[str, float, int, Path]]:
        return {
            param: (value.default if isinstance(value, OptionInfo) else value)
            for param, value in ReflectionTools.default_arg_values(cls.run).items()
            if param not in {"key", "path"}
        }

    @classmethod
    def _get_default_key(cls) -> str:
        vals = ReflectionTools.default_arg_values(cls.run)
        try:
            return vals["key"]
        except KeyError:
            logger.error(f"key not in {vals.keys()} for {cls.__name__}")
            raise


__all__ = ["Entry"]
