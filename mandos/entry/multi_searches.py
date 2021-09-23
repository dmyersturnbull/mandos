"""
Runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Type, Union, Optional, MutableMapping

import pandas as pd
import tomlkit
import typer
from pocketutils.core.exceptions import (
    ReservedError,
    AlreadyUsedError,
    PathExistsError,
    XValueError,
)
from typeddfs import TypedDfs
from tomlkit.api import Table, AoT
from typeddfs.checksums import Checksums
from typeddfs.file_formats import CompressionFormat

from mandos.model.utils.setup import logger, MandosLogging
from mandos.entry.api_singletons import Apis
from mandos.entry.entry_commands import Entries
from mandos.entry.abstract_entries import Entry
from mandos.model.utils.reflection_utils import InjectionError
from mandos.model.hits import HitFrame

cli = typer.Typer()
Apis.set_default()
Chembl, Pubchem = Apis.Chembl, Apis.Pubchem

EntriesByCmd: MutableMapping[str, Type[Entry]] = {e.cmd(): e for e in Entries}

# these are only permitted in 'meta', not individual searches
meta_keys = {"log", "stderr"}
forbidden_keys = {"to", "no_setup"}

SearchExplainDf = (
    TypedDfs.typed("SearchExplainDf")
    .require("key", "search", "source", dtype=str)
    .require("category", "desc", "args", dtype=str)
    .strict()
    .secure()
).build()


@dataclass(frozen=True, repr=True)
class MultiSearch:
    # 'meta' allows us to set defaults for things like --to
    meta: Table
    searches: AoT
    toml_path: Path
    input_path: Path
    out_dir: Path
    suffix: str
    replace: bool
    log_path: Optional[Path]

    @property
    def final_path(self) -> Path:
        name = "search_" + self.input_path.name + "_" + self.toml_path.name + self.suffix
        return self.out_dir / name

    @property
    def explain_path(self) -> Path:
        return Path(str(self.final_path.with_suffix("")) + "_explain.tsv")

    def __post_init__(self):
        if not self.replace and self.final_path.exists():
            raise PathExistsError(f"Path {self.final_path} exists but --replace is not set")
        if not self.replace and self.explain_path.exists():
            raise PathExistsError(f"Path {self.explain_path} exists but --replace is not set")
        for key, value in dict(self.meta).items():
            if key not in meta_keys:
                raise ReservedError(f"{key} in 'meta' not supported.")

    @classmethod
    def build(
        cls,
        input_path: Path,
        out_dir: Path,
        suffix: str,
        toml_path: Path,
        replace: bool,
        log_path: Optional[Path],
    ) -> MultiSearch:
        toml = tomlkit.loads(Path(toml_path).read_text(encoding="utf8"))
        searches = toml.get("search", [])
        return MultiSearch(
            toml.get("meta", []),
            searches,
            toml_path,
            input_path,
            out_dir,
            suffix,
            replace,
            log_path,
        )

    def to_table(self) -> SearchExplainDf:
        rows = []
        for cmd in self._build_commands():
            name = cmd.cmd.get_search_type().search_name()
            cat = cmd.category
            src = cmd.cmd.get_search_type().primary_data_source()
            desc = cmd.cmd.describe()
            args = ", ".join([f"{k}={v}" for k, v in cmd.params.items()])
            ser = dict(key=cmd.key, search=name, category=cat, source=src, desc=desc, args=args)
            rows.append(pd.Series(ser))
        return SearchExplainDf(rows)

    def run(self) -> None:
        # build up the list of Entry classes first, and run ``test`` on each one
        # that's to check that the parameters are correct before running anything
        commands = self._build_commands()
        if len(commands) == 0:
            logger.warning(f"No searches -- nothing to do")
            return
        # write a metadata file describing all of the searches
        explain = self.to_table()
        explain.write_file(self.explain_path, mkdirs=True)
        for cmd in commands:
            cmd.test()
            logger.info(f"Search {cmd.key} looks ok.")
        logger.notice("All searches look ok.")
        for cmd in commands:
            cmd.run()
        logger.notice("Done with all searches!")
        # write the final file
        df = HitFrame(pd.concat([HitFrame.read_file(cmd.output_path) for cmd in commands]))
        df.write_file(self.final_path)
        logger.notice(f"Concatenated file to {self.final_path}")

    def _build_commands(self) -> Sequence[CmdRunner]:
        commands = {}
        skipping = []
        replacing = []
        for search in self.searches:
            cmd = CmdRunner.build(
                search, self.meta, self.input_path, self.out_dir, self.suffix, self.log_path
            )
            if cmd.output_path.exists() and not cmd.done_path.exists():
                logger.error(f"Path {cmd.output_path} exists but not marked as complete.")
            elif cmd.was_run and self.replace:
                replacing += [cmd]
            elif cmd.was_run and not self.replace:
                skipping += [cmd]
            if cmd.key in commands:
                raise AlreadyUsedError(f"Repeated search key '{cmd.key}'")
            if cmd not in skipping:
                commands[cmd.key] = cmd
        if len(skipping) > 0:
            skipping = ", ".join([c.key for c in skipping])
            logger.notice(f"Skipping searches {skipping} (already run).")
        if len(replacing) > 0:
            replacing = ", ".join([c.key for c in skipping])
            logger.notice(f"Overwriting results for searches {replacing}.")
        return list(commands.values())


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
    def build(
        cls,
        e: Table,
        meta: Table,
        input_path: Path,
        out_dir: Path,
        suffix: str,
        cli_log: Optional[Path],
    ):
        cmd = e["source"].value
        key = e.get("key", cmd)
        if "log" in meta:
            if len(meta["log"].value) == 1:
                raise XValueError("'log' is empty")
            log = key + meta["log"].value
            MandosLogging.get_log_suffix(cli_log)  # just check
        elif cli_log is not None:
            log = key + MandosLogging.get_log_suffix(cli_log)
        else:
            log = key + ".log"
        log = out_dir / log
        try:
            cmd = EntriesByCmd[cmd]
        except KeyError:
            raise InjectionError(f"Search command {cmd} (key {key}) does not exist")
        # use defaults
        params = dict(meta)
        # they shouldn't pass any of these args
        bad = {b for b in {*meta_keys, "path", "no_setup", "to"} if b in e}
        if len(bad) > 0:
            raise ReservedError(f"Forbidden keys in [[search]] ({cmd}): {','.join(bad)}")
        # update the defaults from 'meta' (e.g. 'verbose')
        # skip the source -- it's the command name
        # stupidly, we need to explicitly add the defaults from the OptionInfo instances
        params.update(cmd.default_param_values().items())
        # do this after: the defaults had path, key, and to
        params["key"] = key
        params["to"] = out_dir / (key + suffix)
        params["log"] = log
        # now add the params we got for this command's section
        params.update({k: v for k, v in e.items() if k != "source" and k != "category"})
        category = e.get("category")
        return CmdRunner(cmd, params, input_path, category)


__all__ = ["MultiSearch"]
