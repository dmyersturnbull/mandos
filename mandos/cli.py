"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
from typing import Sequence
from pathlib import Path

import typer

from mandos.activity import ActivitySearch

logger = logging.getLogger(__package__)


cli = typer.Typer()


@cli.command()
def activity(inchis_path: Path, write_path: Path) -> None:
    """
    Process activity / binding data.

    Args:

        inchis_path: Path to file containing one InChI per line
        write_path: Path of a CSV file to write
    """


@cli.command()
def mechanism(inchis_path: Path, write_path: Path) -> None:
    """
    Process mechanism of action data.

    Args:

        inchis_path: Path to file containing one InChI per line
        write_path: Path of a CSV file to write
    """


@cli.command()
def act(inchis_path: Path, write_path: Path) -> None:
    """
    Process ATC data.

    Args:

        inchis_path: Path to file containing one InChI per line
        write_path: Path of a CSV file to write
    """


if __name__ == "__main__":
    cli()
