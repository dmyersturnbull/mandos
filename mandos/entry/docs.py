"""
Documents Mandos commands.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Sequence, Mapping
from dataclasses import dataclass
from textwrap import wrap

import pandas as pd
import typer
from typeddfs import TypedDfs, FileFormat
from typeddfs.utils import Utils as TypedDfsUtils
from typer.models import CommandInfo


DocFrame = (
    TypedDfs.typed("DocFrame")
    .require("command", dtype=str)
    .reserve("description", "parameters", dtype=str)
    .strict(cols=False)
    .secure()
).build()


@dataclass(frozen=True, repr=True)
class Documenter:
    level: int
    main: bool
    search: bool
    hidden: bool
    common: bool
    width: int

    def __post_init__(self):
        if self.main and self.search:
            raise ValueError("Cannot provide both --only-main and --only-search")

    def document(self, commands: Sequence[CommandInfo], to: Path, style: str) -> None:
        fmt = FileFormat.from_path_or_none(to)
        if fmt is not None and not fmt.is_text and style != "table":
            raise ValueError(f"Cannot write binary {fmt} with style {style}")
        cmds = [c for c in commands if (self.hidden or not c.hidden)]
        if self.main:
            cmds = [c for c in cmds if c.name.startswith(":")]
        elif self.search:
            cmds = [c for c in cmds if not c.name.startswith(":")]
        cmds = sorted(cmds, key=lambda c: c.name)
        table = DocFrame([self._doc_row(c) for c in cmds])
        self._write(to, table, style)

    def _doc_row(self, c: CommandInfo) -> pd.Series:
        doc = c.callback.__doc__
        args = self._typer_param_docs(c)
        dct = dict(command=c.name)
        # descriptions
        if self.level >= 3:
            dct["description"] = doc
        elif self.level >= 1:
            dct["description"] = [s for s in doc.splitlines() if s.strip() != ""][0]
        # parameters
        if self.level >= 4:
            for i, (k, v) in enumerate(args.items()):
                dct[f"parameter_{i}"] = f"{k} \n\n{v}"
        elif self.level >= 3:
            z = [f"{k}:: {v.splitlines()[0]}" for k, v in args.items()]
            dct["parameters"] = "\n\n".join(z)
        elif self.level == 2:
            dct["parameters"] = " ".join(args.keys())
        return pd.Series(dct)

    def _typer_param_docs(self, c: CommandInfo) -> Mapping[str, str]:
        _args = inspect.signature(c.callback).parameters
        args = {}
        for k, p in _args.items():
            dtype = str(p.annotation)
            v = p.default
            if not isinstance(v, (typer.models.ParameterInfo, typer.models.OptionInfo)):
                raise AssertionError(f"{p} can't be {v} on {c.name}!")
            if isinstance(v, typer.models.OptionInfo):
                k = "--" + k
            k = k.replace("_", "-")
            doc = f"[type: {dtype}] " + v.help
            if (
                (self.hidden or not v.hidden)
                and (self.common or k not in ["--verbose", "--quiet", "--log"])
                and (
                    self.common
                    or c.name.startswith(":")
                    or k not in ["path", "--key", "--to", "--as-of", "--check", "--no-setup"]
                )
            ):
                if v.show_default:
                    args[k] = doc + f"\n[default: {v.default}]"
                else:
                    args[k] = doc
        return args

    def _write(self, to: Path, table: pd.DataFrame, style: str) -> None:
        if style == "table":
            table.write_file(to)
        elif style in ["long", "doc", "long-form"]:
            content = "\n".join(self._long_doc_format(table))
            TypedDfsUtils.write(to, content)
        else:
            table = table.applymap(lambda s: self._format(str(s)))
            content = table.pretty_print(style)
            TypedDfsUtils.write(to, content)

    def _long_doc_format(self, table: pd.DataFrame) -> Sequence[str]:
        lines = []
        for r in range(len(table)):
            row = str(table.iat[r, 0])
            lines += [
                "\n",
                "\n",
                row.center(self.width),
                "\n",
                "=" * self.width,
                "\n",
            ]
            if "description" in table.columns:
                lines += [str(table.iat[r, 1]), "\n", "\n"]
            for c in range(2, len(table.columns)):
                iat = str(table.iat[r, c])
                if iat != "nan":
                    lines += ["\n", "\n", "-" * self.width, "\n", iat]
        return lines

    def _format(self, s: str) -> str:
        s = s.strip()
        if s == "nan":
            return ""
        if self.width == 0:
            return s
        lines = []
        for line in s.split("\n\n"):
            lines.extend(wrap(line, width=self.width))
            lines.append(os.linesep)
        lines = [line.strip(" ").strip("\t") for line in lines]
        return os.linesep.join(lines).replace(os.linesep * 2, os.linesep)


__all__ = ["Documenter"]
