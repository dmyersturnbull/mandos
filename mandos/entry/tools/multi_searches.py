"""
Runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Type, Union

import pandas as pd
import typer
from pocketutils.core.exceptions import InjectionError, PathExistsError
from typeddfs import Checksums, TypedDfs
from typeddfs.abs_dfs import AbsDf

from mandos.entry.abstract_entries import Entry
from mandos.entry.api_singletons import Apis
from mandos.entry.entry_commands import Entries
from mandos.entry.utils._arg_utils import EntryUtils
from mandos.model.hit_dfs import HitDf
from mandos.model.settings import SETTINGS
from mandos.model.utils.setup import LOG_SETUP, logger

cli = typer.Typer()

EntriesByCmd: MutableMapping[str, Type[Entry]] = {e.cmd(): e for e in Entries}

# these are not permitted in individual searches
forbidden_keys = {"to", "stderr", "log", "replace", "proceed"}

SearchExplainDf = (
    TypedDfs.typed("SearchExplainDf")
    .require("key", "search", "source", dtype=str)
    .require("desc", "args", dtype=str)
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
    restart: bool
    proceed: bool
    log_path: Optional[Path]

    @property
    def final_path(self) -> Path:
        name = "search_" + self.input_path.name + self.suffix
        return self.out_dir / name

    @property
    def is_complete(self):
        return Checksums().get_filesum_of_file(self.final_path).exists()

    @property
    def doc_path(self) -> Path:
        return Path(str(self.final_path.with_suffix("")) + ".doc.tsv")

    def test(self) -> None:
        self._build_and_test()

    def run(self) -> None:
        if self.final_path.exists():
            raise PathExistsError(f"{self.final_path} exists")
        commands = self._build_and_test()
        # start!
        for cmd in commands:
            cmd.run()
        logger.notice("Done with all searches!")
        self._write_final(commands)

    def _write_final(self, commands: Sequence[CmdRunner]):
        # write the final file
        df = HitDf(pd.concat([HitDf.read_file(cmd.output_path) for cmd in commands]))
        now = datetime.now().isoformat(timespec="milliseconds")
        docs = self.get_docs(commands)
        SearchExplainDf([pd.Series(x) for x in docs]).write_file(self.doc_path)
        df = df.set_attrs(commands=docs, written=now)
        df.write_file(
            self.final_path.resolve(),
            dir_hash=True,
            file_hash=True,
            attrs=True,
            overwrite=self.restart,
        )
        logger.notice(f"Concatenated results to {self.final_path}")

    def _build_and_test(self) -> Sequence[CmdRunner]:
        # build up the list of Entry classes first, and run ``test`` on each one
        # that's to check that the parameters are correct before running anything
        logger.info("Building commands...")
        commands = self._build_commands()
        if len(commands) == 0:
            logger.warning(f"No searches — nothing to do")
            return []
        # build and test
        for cmd in commands:
            try:
                logger.info(f"Testing {cmd.key} ({cmd.cmd.__name__})")
                cmd.test()
            except Exception:
                logger.error(f"Bad search {cmd}")
                raise
        logger.success("Searches look ok")
        return commands

    def _build_commands(self) -> Sequence[CmdRunner]:
        commands = {}
        for i in range(len(self.config)):
            data = {
                k: v
                for k, v in self.config.iloc[i].to_dict().items()
                if v is not None and not pd.isna(v)
            }
            cmd = self._build_command(data)
            if cmd is not None:
                commands[cmd.key] = cmd
        return list(commands.values())

    def _build_command(self, data):
        key = data["key"]
        with logger.contextualize(key=key):
            default_to = self.out_dir / (key + SETTINGS.table_suffix)
            # not actually replacing -- we're just pretending so we can call adjust_filename
            data["to"] = EntryUtils.adjust_filename(
                None, default=default_to, replace=True, quiet=True
            )
            data["log"] = self._get_log_path(key)
            data["stderr"] = None  # MANDOS_SETUP.main.level
            cmd = CmdRunner.build(data, self.input_path, restart=self.restart, proceed=self.proceed)
        return cmd

    def get_docs(self, commands: Sequence[CmdRunner]) -> Sequence[Mapping[str, Any]]:
        rows = []
        for cmd in commands:
            st = cmd.cmd.get_search_type()
            name = st.search_name()
            src = st.primary_data_source()
            desc = cmd.cmd.describe()
            args = " ".join([f'{k}="{v}"' for k, v in cmd.params.items()])
            ser = dict(key=cmd.key, search=name, source=src, desc=desc, args=args)
            rows.append(ser)
        return rows

    def _get_log_path(self, key: str) -> Path:
        if self.log_path is None:
            suffix = SETTINGS.log_suffix
            return self.out_dir / (key + suffix)
        else:
            suffix = LOG_SETUP.guess_file_sink_info(self.log_path).suffix
            log_base = self.log_path.name[: -len(suffix)]
            return self.log_path.parent / (log_base + "_" + key + suffix)


@dataclass(frozen=True, repr=True)
class CmdRunner:
    cmd: Type[Entry]
    params: MutableMapping[str, Union[int, str, float]]
    input_path: Path

    @property
    def key(self) -> str:
        return self.params["key"]

    @property
    def output_path(self) -> Path:
        return Path(self.params["to"])

    def test(self) -> None:
        with logger.contextualize(key=self.key):
            self.cmd.test(self.input_path, **self.params)

    def run(self) -> None:
        with logger.contextualize(key=self.key):
            self.cmd.run(self.input_path, **self.params)

    @classmethod
    def build(
        cls, data: Mapping[str, Any], input_path: Path, *, restart: bool, proceed: bool
    ) -> CmdRunner:
        key, cmd = data["key"], data["source"]
        try:
            cmd = EntriesByCmd[cmd]
        except KeyError:
            raise InjectionError(f"Search command {cmd} (key {key}) does not exist") from None
        # we need to explicitly add the defaults from the OptionInfo instances
        # add our new stuff after that
        params = {
            **cmd.default_param_values(),
            **dict(replace=restart, proceed=proceed),
            **{k: v for k, v in data.items() if k != "source"},
        }
        return CmdRunner(cmd, params, input_path)


__all__ = ["MultiSearch", "SearchExplainDf", "SearchConfigDf"]
