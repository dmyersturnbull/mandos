"""
Tyrannosaurus command-line interface and processor / main code.
All of its code is here.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import tomlkit
import typer

from .api import Api

logger = logging.getLogger(__package__)

cli = typer.Typer()


@cli.command()
def go(path: Path) -> None:
    if path.exists():
        chembl_ids = path.read_text(encoding='utf8').splitlines()
        #data = tomlkit.loads(Path(path).read_text(encoding="utf8"))
        Api().link()
    typer.echo("Hello! It's {} ({})".format(date.today(), datetime.now()))


if __name__ == "__main__":
    cli()
