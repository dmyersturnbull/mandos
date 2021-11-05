"""
Documents Mandos commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Mapping, Optional, Sequence

import pandas as pd
from pocketutils.core.exceptions import ContradictoryRequestError
from pocketutils.misc.typer_utils import TyperUtils
from typeddfs import FileFormat, TypedDfs
from typeddfs.utils import Utils as TdfUtils
from typer.models import CommandInfo

CommandDocDf = (
    TypedDfs.typed("CommandDocDf")
    .require("command", dtype=str)
    .reserve("description", "parameters", dtype=str)
    .strict()
    .secure()
).build()


@dataclass(frozen=True, repr=True)
class Doc:
    command: str
    description: Optional[str]
    params: Optional[Mapping[str, str]]

    def as_lines(self) -> Sequence[str]:
        lines = [self.command]
        if self.description is not None:
            lines.append(self.description)
        if self.params is not None:
            lines.extend(self.description)
        return lines

    def as_dict(self) -> Mapping[str, str]:
        dct = dict(command=self.command)
        if self.description is not None:
            dct["description"] = self.description
        if self.params is not None:
            dct["params"] = "\n".join(self.params.values())
        return dct


@dataclass(frozen=True, repr=True)
class Documenter:
    level: int
    main: bool
    search: bool
    hidden: bool
    common: bool
    width: Optional[int]

    def document(self, commands: Sequence[CommandInfo], to: Path, style: str) -> None:
        fmt = FileFormat.from_path_or_none(to)
        if fmt is not None and not fmt.is_text and style != "table":
            raise ContradictoryRequestError(f"Cannot write binary {fmt} with style {style}")
        if style == "docs":
            content = self.get_long_text(commands)
            TdfUtils.write(to, content, encoding="utf8")
            return
        table = self.get_table(commands)
        if style == "table":
            table.write_file(to)
        else:
            content = table.pretty_print(style)
            TdfUtils.write(to, content, encoding="utf8")

    def get_table(self, commands: Sequence[CommandInfo]) -> CommandDocDf:
        docs = self.get_docs(commands)
        return CommandDocDf.of([pd.Series(d.as_dict()) for d in docs])

    def get_long_text(self, commands: Sequence[CommandInfo]) -> str:
        if self.search and self.main:
            title = "Main and search commands"
        elif self.search:
            title = "Search commands"
        else:
            title = "Main commands"
        docs = self.get_long(commands)
        width = max([len(title), *[len(s) for s in docs.keys()]])
        txt = title + "\n" + "=" * width + "\n\n"
        for k, v in docs.items():
            txt += "\n\n" + k + "\n" + "#" * width + "\n" + v + "\n"
        return txt

    def get_long(self, commands: Sequence[CommandInfo]) -> Mapping[str, str]:
        docs = self.get_docs(commands)
        results = {}
        for doc in docs:
            zz = []
            for line in doc.as_lines():
                zz += line
            results[doc.command] = "\n".join(zz)
        return results

    def get_docs(self, commands: Sequence[CommandInfo]) -> Sequence[Doc]:
        commands = self._commands(commands)
        return [self._doc(cmd) for cmd in commands]

    def _commands(self, commands: Sequence[CommandInfo]):
        cmds = [
            c
            for c in commands
            if (self.hidden or not c.hidden)
            and (c.name.startswith(":") and self.main or not c.name.startswith(":") and self.search)
        ]
        return sorted(cmds, key=lambda c: c.name)

    def _doc(self, cmd: CommandInfo) -> Doc:
        desc = self._wrap(self._desc(cmd))
        params = TyperUtils.get_help(cmd, hidden=self.hidden)
        params = {
            k: self._wrap(self._param(a))
            for k, a in params.items()
            if self._include_arg(cmd.name, k)
        }
        return Doc(command=self._wrap(cmd.name), description=desc, params=params)

    def _desc(self, cmd: CommandInfo) -> Optional[str]:
        cb = cmd.callback.__doc__
        desc_lines = self._split(cb)
        if self.level >= 3:
            return cb
        elif self.level >= 2:
            return "\n".join(desc_lines[:2])
        elif self.level >= 1:
            return desc_lines[0]
        return None

    def _param(self, param: str) -> Optional[str]:
        lines = self._split(param)
        if self.level >= 3:
            return param
        if self.level >= 2:
            return lines[0] + "\n" + lines[1]
        elif self.level >= 1:
            return lines[0]
        return None

    def _include_arg(self, command: str, arg: str) -> bool:
        if self.common:
            return True
        _common = ["path", "--key", "--to", "--as-of", "--replace", "--proceed", "--check"]
        return arg not in ["--stderr", "--log"] and (command.startswith(":") or arg not in _common)

    def _split(self, txt: str) -> Sequence[str]:
        zs = []
        for s in txt.splitlines():
            s = self._clean(s)
            if len(s) > 0:
                zs.append(s)
        return zs

    def _clean(self, txt: str) -> str:
        return TdfUtils.strip_control_chars(txt.replace("\n", " ").replace("\t", " ")).strip()

    def _wrap(self, txt: Optional[str]) -> Optional[str]:
        if txt is None:
            return None
        if self.width is None:
            return txt
        return "\n".join(wrap(txt, width=self.width))


__all__ = ["CommandDocDf", "Doc", "Documenter"]
