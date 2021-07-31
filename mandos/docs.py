"""
Documents Mandos commands.
"""

from __future__ import annotations

import inspect
import typing
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd
import typer
from typeddfs import TypedDfs, FileFormat
from typeddfs.abs_df import get_handle
from typer.models import CommandInfo


class Documenter:
    def __init__(
        self,
        available: Sequence[CommandInfo],
        main: bool,
        search: bool,
        hidden: bool,
    ):
        cmds = [c for c in available if (hidden or not c.hidden)]
        if main:
            cmds = [c for c in cmds if c.name.startswith(":")]
        elif search:
            cmds = [c for c in cmds if not c.name.startswith(":")]
        self.registered_commands = cmds
        self.hidden = hidden

    def document(self, level: int, to: Path, style: str, replace: bool) -> None:
        _t = TypedDfs.typed("DocFrame").build()
        table = _t([self._doc_row(c, level) for c in self.registered_commands])
        if style != "":
            content = table.pretty_print(style)
            with get_handle(to, "w", encoding="utf8", compression="infer") as f:
                f.handle.write(content)
        else:
            table.write_file(to)

    def _doc_row(self, c: CommandInfo, level: int) -> pd.Series:
        doc = c.callback.__doc__
        args = self._typer_param_docs(c, self.hidden)
        dct = dict(command=c.name)
        # descriptions
        if level >= 3:
            dct["description"] = doc
        elif level >= 1:
            dct["description"] = doc.splitlines()[0]
        # parameters
        if level >= 4:
            for i, (k, v) in enumerate(args.items()):
                dct[f"parameter_{i}"] = f"{k}:: {v}"
        elif level >= 3:
            for i, (k, v) in enumerate(args.items()):
                dct[f"parameter_{i}"] = f"{k}:: {v.splitlines()[0]}"
        elif level == 2:
            dct["parameters"] = " ".join(args.keys())
        return pd.Series(dct)

    def _typer_param_docs(self, c: CommandInfo, hidden: bool) -> Mapping[str, str]:
        _args = inspect.signature(c.callback).parameters
        args = {}
        for k, p in _args.items():
            dtype = str(p.annotation)  # TODO: bad
            v = p.default
            if not isinstance(v, typer.models.ParameterInfo):
                raise AssertionError(f"{p} can't be!")
            if isinstance(v, typer.models.OptionInfo):
                k = "--" + k
            k = k.replace("_", "-")
            k = k.replace("kind", "type")  # TODO: bad
            doc = f"[type: {dtype}] " + inspect.cleandoc(v.help)
            if hidden or not v.hidden:
                if v.show_default:
                    args[k] = doc + f"\n[default: {v.default}]"
                else:
                    args[k] = doc
        return args
