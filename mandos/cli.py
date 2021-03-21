"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
import typer
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.search.entries import Entries

from mandos.search.api_singletons import Apis
from mandos.search.multi_searches import MultiSearch
from mandos.search.searcher import Searcher, SearcherUtils

logger = logging.getLogger(__package__)
# IMPORTANT!
Apis.set_default()
cli = typer.Typer()


class Commands:
    """
    Entry points for mandos.
    """

    @staticmethod
    def search(
        path: Path,
        config: Optional[Path] = None,
    ) -> None:
        """
        Runs multiple searches.

        Args:
            path:
            config:
        """
        MultiSearch(path, config).search()

    @staticmethod
    def find(
        path: Path,
        pubchem: bool = True,
        chembl: bool = True,
    ) -> None:
        """
        Fetches and caches compound data.
        Useful to check what you can see before running a search.
        """
        out_path = path.with_suffix(".ids.csv")
        if out_path.exists():
            raise FileExistsError(out_path)
        inchikeys = SearcherUtils.read(path)
        df = SearcherUtils.dl(inchikeys, pubchem=pubchem, chembl=chembl)
        df.to_csv(out_path)
        typer.echo(f"Wrote to {out_path}")

    @staticmethod
    def dl_tax(
        taxon: int,
    ) -> None:
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
        TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(taxon)


# Oh dear this is a nightmare
# it's really hard to create typer commands with dynamically configured params --
# we really need to rely on its inferring of params
# that makes this really hard to do well
for entry in Entries:
    from typer.models import CommandInfo

    info = CommandInfo(entry.cmd(), callback=entry.run)
    cli.registered_commands.append(info)
    setattr(Commands, entry.cmd(), entry.run)

cli.registered_commands.extend(
    [
        CommandInfo("search", callback=Commands.search),
        CommandInfo("dl_tax", callback=Commands.dl_tax, hidden=True),
    ]
)


if __name__ == "__main__":
    cli()


__all__ = ["Commands", "Searcher"]
