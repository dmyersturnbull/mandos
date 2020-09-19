"""
Command-line interface for mandos.
"""

from __future__ import annotations

import enum
import logging
from pathlib import Path
from typing import Optional, Sequence, Type
from typing import Tuple as Tup

import pandas as pd
import typer
from pocketutils.core.dot_dict import NestedDotDict
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.search.activity_search import ActivitySearch
from mandos.model.settings import Settings
from mandos.search.atc_search import AtcSearch
from mandos.search.mechanism_search import MechanismSearch
from mandos.api import ChemblApi
from mandos.model import Search, Triple
from mandos.model.caches import TaxonomyCache

logger = logging.getLogger(__package__)


cli = typer.Typer()


class What(enum.Enum):
    """
    List of search items
    """

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


class Format(enum.Enum):
    csv = enum.auto()
    text = enum.auto()


class Commands:
    """
    Entry points for mandos.
    """

    @staticmethod
    @cli.command()
    def search(
        what: What,
        path: Path = typer.Option(
            None, "in", exists=True, file_okay=True, dir_okay=True, resolve_path=True
        ),
        config: Optional[Path] = None,
    ) -> None:
        """
        Process data.

        Args:
            what: Activity / ATCs / mechanisms / etc.
            path: Path to file containing one InChI per line
            config: Path to a TOML config file
        """
        data = path.read_bytes()
        compounds = data.decode(encoding="utf8").splitlines()
        df, triples = Commands.search_for(what, compounds, config=config)
        df_out = Path(str(path.with_suffix("")) + "-" + what.name.lower() + ".csv")
        df.to_csv(df_out)
        triples_out = df_out.with_suffix(".triples.txt")
        triples_out.write_text("\n".join([t.statement for t in triples]), encoding="utf8")

    @staticmethod
    @cli.command(hidden=True)
    def process_tax(taxon: int) -> None:
        """
        Preps a new taxonomy file for use in mandos.
        Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
        Otherwise, downloads a tab-separated file from UniProt.
        (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
        Then applies fixes and reduces the file size, creating a new file alongside.
        Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.

        Args:
            taxon: The **ID** of the UniProt taxon
        """
        TaxonomyCache(taxon).load()

    @staticmethod
    def search_for(
        what: What, compounds: Sequence[str], config: Optional[Path]
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """

        Args:
            what:
            compounds:
            config:

        Returns:

        """
        settings = Settings.load({} if config is None else NestedDotDict.read_toml(config))
        settings.set()
        compounds = list(compounds)
        api = ChemblApi.wrap(Chembl)
        hits = what.clazz(api, settings).find_all(compounds)
        # collapse over and sort the triples
        triples = sorted(list({hit.to_triple() for hit in hits}))
        df = pd.DataFrame(
            [pd.Series({f: getattr(h, f) for f in what.clazz.hit_fields()}) for h in hits]
        )
        return df, triples


if __name__ == "__main__":
    cli()


__all__ = ["Commands", "What"]
