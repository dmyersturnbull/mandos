"""
Command-line interface for mandos.
"""

from __future__ import annotations

import enum
import logging
from pathlib import Path, PurePath
from typing import Any, Mapping, Optional, Sequence
from typing import Tuple as Tup
from typing import Type, Union

import pandas as pd
import typer
from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

from mandos.api import ChemblApi
from mandos.model import Search, Triple
from mandos.model.caches import TaxonomyCache, TaxonomyCaches
from mandos.model.settings import Settings
from mandos.search.activity_search import ActivitySearch
from mandos.search.atc_search import AtcSearch
from mandos.search.indication_search import IndicationSearch
from mandos.search.mechanism_search import MechanismSearch

logger = logging.getLogger(__package__)


cli = typer.Typer()


class What(enum.Enum):
    """
    List of search items.
    """

    activity = enum.auto(), ActivitySearch
    mechanism = enum.auto(), MechanismSearch
    atc = enum.auto(), AtcSearch
    trial = enum.auto(), IndicationSearch

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
    """
    Entry points for mandos.
    """

    @staticmethod
    @cli.command()
    def search(
        what: str,
        path: Path,
        config: Optional[Path] = None,
    ) -> None:
        """
        Process data.

        Args:
            what: Comma-separated list of ``activity``, ``mechanism``, ``atc``, and ``indication``.
            path: Path to file containing one InChI per line
            config: Path to a TOML config file
        """
        for w in what.split(","):
            w = What[w.lower()]
            df, triples = Commands.search_for(w, path, config=config)
            df_out = Path(str(path.with_suffix("")) + "-" + w.name.lower() + ".csv")
            df.to_csv(df_out)
            triples_out = df_out.with_suffix(".triples.txt")
            triples_out.write_text("\n".join([t.statement for t in triples]), encoding="utf8")
            triples_out.write_text(
                "\n".join([Triple.tab_header(), *[t.tabs for t in triples]]), encoding="utf8"
            )

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
        TaxonomyCaches.load(taxon)

    @staticmethod
    def search_for(
        what: What,
        compounds: Union[Sequence[str], PurePath],
        config: Union[None, Mapping[str, Any], Path],
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """

        Args:
            what:
            compounds:
            config:

        Returns:

        """
        if isinstance(compounds, (PurePath, str)):
            compounds = Path(compounds).read_text(encoding="utf8").splitlines()
        compounds = [c.strip() for c in compounds if len(c.strip()) > 0]
        if config is None:
            settings = Settings.load(NestedDotDict({}))
        elif isinstance(config, PurePath):
            settings = Settings.load(NestedDotDict.read_toml(config))
        elif isinstance(config, NestedDotDict):
            settings = config
        else:
            settings = Settings.load(NestedDotDict(config))
        settings.set()
        compounds = list(compounds)
        api = ChemblApi.wrap(Chembl)
        taxonomy = TaxonomyCaches.load(settings.taxon)
        hits = what.clazz(api, settings, taxonomy).find_all(compounds)
        # collapse over and sort the triples
        triples = sorted(list({hit.to_triple() for hit in hits}))
        df = pd.DataFrame(
            [pd.Series({f: getattr(h, f) for f in what.clazz.hit_fields()}) for h in hits]
        )
        return df, triples


if __name__ == "__main__":
    cli()


__all__ = ["Commands", "What"]
