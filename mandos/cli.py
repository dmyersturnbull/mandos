"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from mandos import logger
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.entries.entries import Entries, _Typer
from mandos.entries.api_singletons import Apis
from mandos.entries.multi_searches import MultiSearch
from mandos.entries.searcher import SearcherUtils

# IMPORTANT!
Apis.set_default()
cli = typer.Typer()


class Commands:
    """
    Entry points for mandos.
    """

    @staticmethod
    def search(
        path: Path = _Typer.path,
        config: Path = typer.Argument(
            None,
            help=".toml config file. See docs.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ) -> None:
        """
        Run multiple searches.
        """
        MultiSearch(path, config).search()

    @staticmethod
    def find(
        path: Path = _Typer.path,
        pubchem: bool = typer.Option(True, help="Download data from PubChem"),
        chembl: bool = typer.Option(True, help="Download data from ChEMBL"),
        hmdb: bool = typer.Option(True, help="Download data from HMDB"),
    ) -> None:
        """
        Fetches and caches compound data.
        Useful to check what you can see before running a search.
        """
        out_path = path.with_suffix(".ids.csv")
        if out_path.exists():
            raise FileExistsError(out_path)
        inchikeys = SearcherUtils.read(path)
        df = SearcherUtils.dl(inchikeys, pubchem=pubchem, chembl=chembl, hmdb=hmdb)
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
    # print(f"Registered {entry.cmd()} to {entry}")
    setattr(Commands, entry.cmd(), entry.run)

cli.registered_commands.extend(
    [
        CommandInfo("@search", callback=Commands.search),
        CommandInfo("@dl-tax", callback=Commands.dl_tax, hidden=True),
    ]
)


if __name__ == "__main__":
    # logging.basicConfig(level=0)
    import sys

    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(0)
    formatter = logging.Formatter("%(levelname)-7s %(asctime)s %(message)s", "%Y%m%d:%H:%M:%S")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    # log_factory = PrettyRecordFactory(10, 12, 5, width=100, symbols=True).modifying(logger)
    # good start; can be changed
    root.setLevel(logging.WARNING)
    logger.setLevel(logging.INFO)
    cli()


__all__ = ["Commands"]
