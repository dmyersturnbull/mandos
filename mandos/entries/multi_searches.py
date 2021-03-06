"""
Runner.
"""

from __future__ import annotations

import typing
from pathlib import Path
from typing import Optional, Union, Type

import typer
from pocketutils.core.dot_dict import NestedDotDict

from mandos import MandosLogging
from mandos.entries import EntryMeta
from mandos.model import InjectionError, ReflectionUtils
from mandos.entries.entries import Entries, Entry
from mandos.entries.api_singletons import Apis

cli = typer.Typer()
Apis.set_default()
Chembl, Pubchem = Apis.Chembl, Apis.Pubchem

EntriesByCmd: typing.Dict[str, Type[Entry]] = {e.cmd(): e for e in Entries}

# these are only permitted in 'meta', not individual searches
meta_keys = {"verbose", "quiet", "check", "log", "to"}


class MultiSearch:
    """
    Ugh.
    """

    # ------------------------
    # TODO: This code is nightmarishly complex.
    # ------------------------

    def __init__(self, path: Path, config: Optional[Path]):
        if config is None:
            config = path.with_suffix(".toml")
        self.path = path
        if not self.path.exists():
            raise FileNotFoundError(f"File {path} not found")
        if not config.exists():
            raise FileNotFoundError(f"File {config} not found")
        toml = NestedDotDict.read_toml(config)
        self.toml_searches = toml.get_as("search", list, [])
        # 'meta' allows us to set defaults
        # for now, I'm only allowing true "metadata" keys
        self.meta = toml.sub("meta")
        # TODO: allow specifying a directory, not just format (suffix)
        self.format = self.meta.get_as("to", str, ".feather")
        if not self.format.startswith("."):
            raise ValueError(
                f"Value to='{self.format}' does not start with '.'. Only a filename extension is permitted."
            )
        for key, value in self.meta.items():
            if key not in meta_keys:
                raise ValueError(
                    f"Found {key}={value} in 'meta' of TOML. Only {', '.join(meta_keys)} are supported."
                )

    def search(self) -> None:
        cmds = self._build_commands()
        # this is terrible
        EntryMeta.set_logging(
            quiet=self.meta.get("quiet", False),
            verbose=self.meta.get("verbose", False),
            log=self.meta.get("log", None),
        )
        for key, (ent, params) in cmds.items():
            ent.run(self.path, **{**params, **dict(no_setup=True, check=False)})

    def _build_commands(
        self,
    ) -> typing.Dict[str, typing.Tuple[Type[Entry], typing.Mapping[str, Union[int, str, float]]]]:
        commands: typing.Dict[
            str, typing.Tuple[Type[Entry], typing.Mapping[str, Union[int, str, float]]]
        ] = {}
        # build up the lit of Entry classes first, and run ``test`` on each one
        # that's to check that the parameters are correct before running anything
        for e in self.toml_searches:
            e = NestedDotDict(e)
            cmd = e.req_as("source", str)
            key = e.get_as("key", str, cmd)
            try:
                cmd = EntriesByCmd[cmd]
            except KeyError:
                raise InjectionError(f"Search command {cmd} (key {key}) does not exist")
            # use defaults
            params = dict(self.meta)
            # they shouldn't pass any of these args
            if "path" in e:
                raise ValueError(f"Cannot set 'path' in [[search]]")
            for bad in {*meta_keys, "no_setup"}:
                if bad in e:
                    raise ValueError(f"Cannot set '{bad}' in [[search]]; set in meta")
            # update the defaults from 'meta' (e.g. 'verbose')
            # skip the source -- it's the command name
            # stupidly, we need to explicitly add the defaults from the OptionInfo instances
            params.update(cmd.default_param_values().items())
            # do this after: the defaults had path, key, and to
            # params["path"] = self.path
            params["key"] = key
            params["to"] = self.format
            params.update({k: v for k, v in e.items() if k != "source"})
            del params["check"]
            cmd.test(self.path, **{**params, **dict(quiet=True)})
            if key in commands:
                raise ValueError(f"Repeated search key '{key}'")
            commands[key] = (cmd, params)
        if self.meta.get("check", False):
            # we already ran check on all of them
            return {}
        else:
            return commands


__all__ = ["MultiSearch"]
