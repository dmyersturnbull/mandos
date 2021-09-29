"""
Runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Type, Union

import pandas as pd
import typer
from pocketutils.core.exceptions import PathExistsError
from typeddfs import TypedDfs
from typeddfs.abs_dfs import AbsDf
from typeddfs.checksums import Checksums
from typeddfs.utils import Utils

from mandos.entry._arg_utils import EntryUtils
from mandos.entry.abstract_entries import Entry
from mandos.entry.api_singletons import Apis
from mandos.entry.entry_commands import Entries
from mandos.model.hit_dfs import HitDf
from mandos.model.settings import SETTINGS
from mandos.model.utils.reflection_utils import InjectionError
from mandos.model.utils.setup import MandosLogging, logger, LogSinkInfo

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


def _no_duplicate_keys(self: AbsDf):
    group = self[["key"]].groupby("key").count().to_dict()
    bad = {k for k, v in group.items() if v > 1}
    if len(bad) > 0:
        return f"Duplicate keys: {', '.join(bad)}"


def _no_illegal_cols(self: AbsDf):
    if "to" in self.columns:
        return "Illegal key 'to'"
    if "path" in self.columns:
        return "Illegal key 'path'"


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
    log_path: Optional[Path]

    @property
    def final_path(self) -> Path:
        name = "search_" + self.input_path.name + self.suffix
        return self.out_dir / name

    @property
    def doc_path(self) -> Path:
        return Path(str(self.final_path.with_suffix("")) + "_doc.tsv")

    def __post_init__(self):
        if not self.replace and self.final_path.exists():
            raise PathExistsError(f"Path {self.final_path} exists but --replace is not set")
        if not self.replace and self.doc_path.exists():
            raise PathExistsError(f"Path {self.doc_path} exists but --replace is not set")

    def run(self) -> None:
        # build up the list of Entry classes first, and run ``test`` on each one
        # that's to check that the parameters are correct before running anything
        commands = self._build_commands()
        if len(commands) == 0:
            logger.warning(f"No searches; nothing to do")
            return
        # write a file describing all of the searches
        self.write_docs(commands)
        # build and test
        for cmd in commands:
            try:
                cmd.test()
            except Exception:
                logger.error(f"Bad search {cmd}")
                raise
        logger.notice("Searches look ok.")
        # start!
        for cmd in commands:
            cmd.run()
        logger.notice("Done with all searches!")
        # write the final file
        df = HitDf(pd.concat([HitDf.read_file(cmd.output_path) for cmd in commands]))
        df.write_file(self.final_path, file_hash=True)
        logger.notice(f"Concatenated file to {self.final_path}")

    def _build_commands(self) -> Sequence[CmdRunner]:
        commands = {}
        for i in range(len(self.config)):
            data = {
                k: v
                for k, v in self.config.iloc[i].to_dict().items()
                if v is not None and not pd.isna(v)
            }
            key = data["key"]
            default_to = self.input_path.parent / (key + SETTINGS.table_suffix)
            data["to"] = EntryUtils.adjust_filename(None, default=default_to, replace=self.replace)
            data["log"] = self._get_log_path(key)
            cmd = CmdRunner.build(data, self.input_path)
            commands[cmd.key] = cmd
        # log about replacing
        replacing = {k for k, v in commands.items() if v.was_run}
        if len(replacing) > 0:
            replacing = Utils.join_to_str(replacing, last="and")
            logger.notice(f"Overwriting results for {replacing}.")
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
        return Checksums.get_hash_dir(self.output_path.parent)

    @property
    def was_run(self) -> bool:
        if not self.done_path.exists():
            return False
        sums = Checksums.parse_hash_file_resolved(self.done_path)
        return self.output_path in sums

    def test(self) -> None:
        self.cmd.test(self.input_path, **self.params)

    def run(self) -> None:
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
        if runner.output_path.exists() and not runner.done_path.exists():
            logger.error(f"Path {runner.output_path} exists but not marked as complete.")
        return runner


__all__ = ["MultiSearch", "SearchExplainDf", "SearchConfigDf"]
