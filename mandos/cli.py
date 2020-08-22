"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
from typing import Sequence

import typer

from mandos.find import BindingSearch

logger = logging.getLogger(__package__)


cli = typer.Typer()


def x(inchis: Sequence[str]) -> None:
    """
    Args:

        inchis: List of InChI strings
    """


if __name__ == "__main__":
    cli()
