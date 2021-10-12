"""
Runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Type, Union

import pandas as pd
import typer
from pocketutils.core.exceptions import (
    IllegalStateError,
    InjectionError,
    PathExistsError,
)
from pocketutils.misc.fancy_loguru import LogSinkInfo
from typeddfs import TypedDfs
from typeddfs.abs_dfs import AbsDf
from typeddfs.checksums import Checksums
from typeddfs.utils import Utils

from mandos import logger
from mandos.entry.abstract_entries import Entry
from mandos.entry.api_singletons import Apis
from mandos.entry.entry_commands import Entries
from mandos.entry.utils._arg_utils import EntryUtils
from mandos.model.hit_dfs import HitDf
from mandos.model.settings import SETTINGS

cli = typer.Typer()
Apis.set_default()
Chembl, Pubchem = Apis.Chembl, Apis.Pubchem

EntriesByCmd: MutableMapping[str, Type[Entry]] = {e.cmd(): e for e in Entries}

# these are not permitted in individual searches
forbidden_keys = {"to", "no_setup"}

SearchExplainDf = (
    TypedDfs.typed("SearchExplainDf")
    .require("key", "search", "source", dtype=str)
    .require("desc", "args", dtype=str)
    .reserve("category", dtype=str)
    .strict()
    .secure()
).build()


def _no_duplicate_keys(self: AbsDf) -> Optional[str]:
    group = self[["key"]].groupby("key").count().to_dict()
    bad = {k for k, v in group.items() if v > 1}
    if len(bad) > 0:
        return f"Duplicate keys: {', '.join(bad)}"
    return None


def _no_illegal_cols(self: AbsDf) -> Optional[str]:
    illegal = {c for c in ["to", "path"] if c in self.columns}
    if len(illegal) > 0:
        return f"Illegal keys {', '.join(illegal)}"
    return None


SearchConfigDf = (
    TypedDfs.typed("SearchConfigDf")
    .require("key", "source", dtype=str)
    .verify(_no_duplicate_keys)
    .verify(_no_illegal_cols)
    .add_read_kwargs("toml", aot="search")
    .add_write_kwargs("toml", aot="search")
    .secure()
    .build()
)


@dataclass(frozen=True, repr=True)
class MultiSearch:
    config: SearchConfigDf
    input_path: Path
    out_dir: Path
    suffix: str
    replace: bool
    proceed: bool
    log_path: Optional[Path]

    @property
    def final_path(self) -> Path:
        name = "search_" + self.input_path.name + self.suffix
        return self.out_dir / name

    @property
    def final_checksum_path(self) -> Path:
        return Checksums.get_hash_file(self.final_path, algorithm=SETTINGS.search_checksum_alg)

    @property
    def is_complete(self):
        return self.final_checksum_path.exists()

    @property
    def doc_path(self) -> Path:
        return Path(str(self.final_path.with_suffix("")) + "_doc.tsv")

    def __post_init__(self):
        if not self.replace and self.is_complete:
            raise PathExistsError(f"Path {self.final_path} is complete but --replace is not set")
        if not self.proceed and self.final_path.exists():
            raise PathExistsError(f"Path {self.final_path} exists but --proceed is not set")

    def run(self) -> None:
        # build up the list of Entry classes first, and run ``test`` on each one
        # that's to check that the parameters are correct before running anything
        commands = self._build_commands()
        if len(commands) == 0:
            logger.warning(f"No searches — nothing to do")
            return
        # write a file describing all of the searches
        self.write_docs(commands)
        # build and test
        for cmd in commands:
            try:
                cmd.test(replace=self.replace, proceed=self.proceed)
            except Exception:
                logger.error(f"Bad search {cmd}")
                raise
        logger.notice("Searches look ok")
        # start!
        for cmd in commands:
            cmd.run(replace=self.replace, proceed=self.proceed)
        logger.notice("Done with all searches!")
        # write the final file
        df = HitDf(pd.concat([HitDf.read_file(cmd.output_path) for cmd in commands]))
        df.write_file(self.final_path, file_hash=True)
        logger.notice(f"Concatenated results to {self.final_path}")

    def _build_commands(self) -> Sequence[CmdRunner]:
        commands = {}
        for i in range(len(self.config)):
            data = {
                k: v
                for k, v in self.config.iloc[i].to_dict().items()
                if v is not None and not pd.isna(v)
            }
            key = data["key"]
            with logger.contextualize(key=key):
                default_to = self.out_dir / (key + SETTINGS.table_suffix)
                # TODO: produces bad logging about being overwritten
                data["to"] = EntryUtils.adjust_filename(None, default=default_to, replace=True)
                data["log"] = self._get_log_path(key)
                cmd = CmdRunner.build(data, self.input_path)
                commands[cmd.key] = cmd
        # log about replacing
        replacing = {k for k, v in commands.items() if v.was_run}
        if len(replacing) > 0:
            replacing = Utils.join_to_str(replacing, last="and")
            logger.notice(f"Overwriting results for {replacing}")
        return list(commands.values())

    def write_docs(self, commands: Sequence[CmdRunner]) -> None:
        rows = []
        for cmd in commands:
            name = cmd.cmd.get_search_type().search_name()
            cat = cmd.category
            src = cmd.cmd.get_search_type().primary_data_source()
            desc = cmd.cmd.describe()
            args = ", ".join([f"{k}={v}" for k, v in cmd.params.items()])
            ser = dict(key=cmd.key, search=name, category=cat, source=src, desc=desc, args=args)
            rows.append(pd.Series(ser))
        df = SearchExplainDf(rows)
        df.write_file(self.doc_path, mkdirs=True)

    def _get_log_path(self, key: str):
        if self.log_path is None:
            suffix = SETTINGS.log_suffix
        else:
            suffix = LogSinkInfo.guess(self.log_path).suffix
        return self.out_dir / (key + suffix)


@dataclass(frozen=True, repr=True)
class CmdRunner:
    cmd: Type[Entry]
    params: MutableMapping[str, Union[int, str, float]]
    input_path: Path
    category: Optional[str]

    @property
    def key(self) -> str:
        return self.params["key"]

    @property
    def output_path(self) -> Path:
        return Path(self.params["to"])

    @property
    def done_path(self) -> Path:
        return Checksums.get_hash_dir(self.output_path, algorithm=SETTINGS.search_checksum_alg)

    @property
    def was_run(self) -> bool:
        if not self.done_path.exists():
            return False
        sums = Checksums.parse_hash_file_resolved(self.done_path)
        done = self.output_path in sums
        if done and not self.output_path.exists():
            raise IllegalStateError(f"{self.output_path} marked complete but does not exist")
        return done

    def test(self, *, replace: bool, proceed: bool) -> None:
        if self.output_path.exists() and not self.was_run and not proceed and not replace:
            raise PathExistsError(f"Path {self.output_path} exists but not finished")
        with logger.contextualize(key=self.key):
            self.cmd.test(self.input_path, **self.params)

    def run(self, *, replace: bool, proceed: bool) -> None:
        # we already checked that we're allowed to proceed
        if replace or not self.was_run:
            with logger.contextualize(key=self.key):
                self.cmd.run(self.input_path, **self.params)

    @classmethod
    def build(cls, data: Mapping[str, Any], input_path: Path):
        key, cmd = data["key"], data["source"]
        try:
            cmd = EntriesByCmd[cmd]
        except KeyError:
            raise InjectionError(f"Search command {cmd} (key {key}) does not exist") from None
        params = {}
        # we need to explicitly add the defaults from the OptionInfo instances
        params.update(cmd.default_param_values().items())
        # do this after: the defaults had path, key, and to
        params["key"] = key
        # now add the params we got for this command's section
        params.update({k: v for k, v in data.items() if k != "source" and k != "category"})
        category = data.get("category")
        runner = CmdRunner(cmd, params, input_path, category)
        return runner


__all__ = ["MultiSearch", "SearchExplainDf", "SearchConfigDf"]
