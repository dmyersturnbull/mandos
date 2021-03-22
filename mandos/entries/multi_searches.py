"""
Runner.
"""

from __future__ import annotations

import logging
import typing
from pathlib import Path
from typing import Optional, Union, Type
import typer
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model import InjectionError
from mandos.entries.entries import Entries, Entry

from mandos.entries.api_singletons import Apis

logger = logging.getLogger(__package__)
cli = typer.Typer()
Apis.set_default()
Chembl, Pubchem = Apis.Chembl, Apis.Pubchem

EntriesByCmd = {e.cmd(): e for e in Entries}


class MultiSearch:
    """
    Ugh.
    """

    def __init__(self, path: Path, config: Optional[Path]):
        if config is None:
            config = path.with_suffix(".toml")
        self.path = path
        if not self.path.exists():
            raise FileNotFoundError(f"File {path} not found")
        if not config.exists():
            raise FileNotFoundError(f"File {config} not found")
        self.toml_searches = NestedDotDict.read_toml(config).get_as("search", list, [])

    def search(self) -> None:
        cmds = self._build_commands()
        for key, (ent, params) in cmds.items():
            ent.run(self.path, **params)

    def _build_commands(
        self,
    ) -> typing.Dict[str, typing.Tuple[Type[Entry], typing.Mapping[str, Union[int, str, float]]]]:
        commands: typing.Dict[
            str, typing.Tuple[Type[Entry], typing.Mapping[str, Union[int, str, float]]]
        ] = {}
        for e in self.toml_searches:
            cmd = e.req_as("source", str)
            key = e.req_as("key", str)
            params = {k: v for k, v in e.items() if k != "source"}
            try:
                cmd = EntriesByCmd[cmd]
            except KeyError:
                raise InjectionError(f"Search command {cmd} (key {key}) does not exist")
            cmd.test(self.path, **params)
            if key in commands:
                raise ValueError(f"Repeated search key '{key}'")
            commands[key] = (cmd, params)
        return commands


__all__ = ["MultiSearch"]
