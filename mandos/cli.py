"""
Command-line interface for mandos.
"""

from __future__ import annotations

import enum
import logging
from pathlib import Path
from typing import Optional, Sequence, Type

import pandas as pd
import typer
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.activity import ActivitySearch
from mandos.atcs import AtcSearch
from mandos.mechanisms import MechanismSearch
from mandos.model import ChemblApi, Search
from mandos.model.taxonomy import Taxonomy

logger = logging.getLogger(__package__)


cli = typer.Typer()


class What(enum.Enum):
    activity = enum.auto(), ActivitySearch
    mechanism = enum.auto(), MechanismSearch
    atc = enum.auto(), AtcSearch

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, clazz: Type[Search]):
        self._clazz_ = clazz

    @property
    def clazz(self) -> Type[Search]:
        return self._clazz_


class Commands:
    @staticmethod
    @cli.command()
    def search(
        what: What,
        inchis_path: Optional[Path] = None,
        write_path: Optional[Path] = None,
        tax_parent: Optional[str] = None,
    ) -> None:
        """
        Process data.

        Args:
            what: Activity / ATCs / mechanisms / etc.
            inchis_path: Path to file containing one InChI per line
            write_path: Path of a CSV file to write
            tax_parent: Restrict to organisms under this tax ID or name
        """
        compounds = inchis_path.read_text(encoding="utf8").splitlines()
        df = Commands.search_for(what, compounds, tax_parent=tax_parent)
        df.to_csv(write_path)

    @staticmethod
    def search_for(what: What, compounds: Sequence[str], tax_parent: Optional[str] = None):
        tax = Commands._tax(tax_parent)
        compounds = list(compounds)
        api = ChemblApi.wrap(Chembl)
        hits = what.clazz(api, tax).find_all(compounds)
        df = pd.DataFrame(
            [pd.Series({f: getattr(h, f) for f in what.clazz.hit_fields()}) for h in hits]
        )
        return df

    @staticmethod
    def _tax(lookup: Optional[str] = None) -> Taxonomy:
        df = pd.read_csv(
            Path(__file__).parent.parent / "mandos" / "resources" / "taxonomy-ancestor_7742.tab.gz",
            sep="\t",
        )
        tax = Taxonomy.from_df(df)
        if lookup is None:
            return tax
        else:
            return tax.under(int(lookup) if lookup.isdigit() else lookup)


if __name__ == "__main__":
    cli()
