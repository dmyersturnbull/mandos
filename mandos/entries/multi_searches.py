"""
Runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence, List, Type, Union, Optional

import pandas as pd
import typer
from typeddfs import TypedDfs
from pocketutils.core.dot_dict import NestedDotDict

from mandos import logger
from mandos.entries.api_singletons import Apis
from mandos.entries.entries import Entries, Entry
from mandos.model import InjectionError
from mandos.model.hits import HitFrame
from mandos.model.settings import MANDOS_SETTINGS

cli = typer.Typer()
Apis.set_default()
Chembl, Pubchem = Apis.Chembl, Apis.Pubchem

EntriesByCmd: Dict[str, Type[Entry]] = {e.cmd(): e for e in Entries}

# these are only permitted in 'meta', not individual searches
meta_keys = {"verbose", "quiet", "check", "log", "to"}
forbidden_keys = {"dir", "out-dir", "out_dir"}

SearchExplainDf = (
    TypedDfs.typed("SearchExplainDf")
    .require("key", "search", "source", dtype=str)
    .require("category", "desc", "args", dtype=str)
).build()


@dataclass(frozen=True, repr=True)
class MultiSearch:
    # 'meta' allows us to set defaults for things like --to
    meta: NestedDotDict
    searches: Sequence[NestedDotDict]
    toml_path: Path
    input_path: Path
    out_dir: Path

    @property
    def final_path(self) -> Path:
        if "to" in self.meta:
            fmt = Path(self.meta["to"]).suffix
        else:
            fmt = MANDOS_SETTINGS.default_table_suffix
        return self.out_dir / ("search_" + self.input_path.name + "_" + self.toml_path.name + fmt)

    @property
    def explain_path(self) -> Path:
        return Path(str(self.final_path.with_suffix("")) + "_explain.tsv")

    def __post_init__(self):
        to = self.meta.get_as("to", str)
        if to is not None and not to.startswith("."):
            raise ValueError(f"Argument 'to' ({to})' must start with '.'.")
        for key, value in self.meta.items():
            if key not in meta_keys:
                raise ValueError(f"{key} in 'meta' not supported.")

    @classmethod
    def build(cls, input_path: Path, out_dir: Path, toml_path: Path) -> MultiSearch:
        toml = NestedDotDict.read_toml(toml_path)
        searches = toml.get_as("search", list, [])
        meta = toml.sub("meta")
        return MultiSearch(meta, searches, toml_path, input_path, out_dir)

    def to_table(self) -> SearchExplainDf:
        rows = []
        for cmd in self._build_commands():
            name = cmd.cmd.get_search_type().search_name
            cat = cmd.category
            src = cmd.cmd.get_search_type()(cmd.key).data_source
            desc = cmd.cmd.describe()
            args = ", ".join([f"{k}={v}" for k, v in cmd.params.items()])
            ser = dict(key=cmd.key, search=name, category=cat, source=src, desc=desc, args=args)
            rows.append(pd.Series(ser))
        return SearchExplainDf(rows)

    def run(self) -> None:
        # build up the list of Entry classes first, and run ``test`` on each one
        # that's to check that the parameters are correct before running anything
        commands = self._build_commands()
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
        # write a metadata file describing all of the searches
        explain = self.to_table()
        explain.write_file(self.explain_path)

    def _build_commands(self) -> Sequence[CmdRunner]:
        commands = {}
        skipping = []
        for search in self.searches:
            cmd = CmdRunner.build(search, self.meta, self.input_path, self.out_dir)
            if cmd.was_run:
                skipping += [cmd]
            else:
                commands[cmd.key] = cmd
                if cmd.key in commands:
                    raise ValueError(f"Repeated search key '{cmd.key}'")
        if len(skipping) > 0:
            skipping = ", ".join([c.key for c in skipping])
            logger.notice(f"Skipping searches {skipping} (already run).")
        return list(commands.values())


@dataclass(frozen=True, repr=True)
class CmdRunner:
    cmd: Type[Entry]
    params: Dict[str, Union[int, str, float]]
    input_path: Path
    category: Optional[str]

    @property
    def key(self) -> str:
        return self.params["key"]

    @property
    def output_path(self) -> Path:
        return Path(self.params["to"])

    @property
    def was_run(self) -> bool:
        return self.done_path.exists()

    @property
    def done_path(self) -> Path:
        return self.output_path.with_suffix(self.output_path.suffix + ".done")

    def test(self) -> None:
        self.cmd.test(self.input_path, **{**self.params, **dict(quiet=True)})

    def run(self) -> None:
        self.cmd.run(self.input_path, **{**self.params, **dict(no_setup=True, check=False)})

    @classmethod
    def build(cls, e: NestedDotDict, meta: NestedDotDict, input_path: Path, out_dir: Path):
        cmd = e.req_as("source", str)
        key = e.get_as("key", str, cmd)
        to = meta.get_as("to", str, MANDOS_SETTINGS.default_table_suffix)
        try:
            cmd = EntriesByCmd[cmd]
        except KeyError:
            raise InjectionError(f"Search command {cmd} (key {key}) does not exist")
        # use defaults
        params = dict(meta)
        # they shouldn't pass any of these args
        bad = {b for b in {*meta_keys, "path", "no_setup", "out_dir"} if b in e}
        if len(bad) > 0:
            raise ValueError(f"Forbidden keys in [[search]] ({cmd}): {','.join(bad)}")
        # update the defaults from 'meta' (e.g. 'verbose')
        # skip the source -- it's the command name
        # stupidly, we need to explicitly add the defaults from the OptionInfo instances
        params.update(cmd.default_param_values().items())
        # do this after: the defaults had path, key, and to
        params["key"] = key
        params["path"] = e.req_as("path", Path)
        params["out_dir"] = out_dir
        params.setdefault("to", to)
        # now add the params we got for this command's section
        params.update({k: v for k, v in e.items() if k != "source" and k != "category"})
        del params["check"]
        category = e.get_as("category", str)
        return CmdRunner(cmd, params, input_path, category)


__all__ = ["MultiSearch"]
