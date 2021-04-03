"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Type

import pandas as pd
import typer
from typer.models import CommandInfo
from typeddfs import TypedDfs

from mandos import logger, MandosLogging
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy import TaxonomyDf
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.entries.entries import Entries
from mandos.entries.args import EntryArgs
from mandos.entries.api_singletons import Apis
from mandos.entries.multi_searches import MultiSearch
from mandos.entries.searcher import SearcherUtils

cli = typer.Typer()


class Commands:
    """
    Entry points for mandos.
    """

    @staticmethod
    def search(
        config: Path = typer.Argument(
            None,
            help=".toml config file. See docs.",
            exists=True,
            dir_okay=False,
            readable=True,
        )
    ) -> None:
        """
        Run multiple searches.
        """
        MultiSearch(path, config).search()

    @staticmethod
    def find(
        path: Path = EntryArgs.path,
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
    def build_taxonomy(
        taxa: str = EntryArgs.taxa,
        to: Path = typer.Option(
            None,
            show_default=False,
            help="""
        Output file; can be CSV, TSV, feather, etc.
        If it starts with '.', uses the default path but changes the format and filename extension.

        [default: <taxon-id,<taxon-id>,...>.feather]
        """,
        ),
    ):
        """
        Writes a CSV file of the descendents of given taxa.
        """
        taxon_ids = [
            int(taxon.strip()) if taxon.strip().isdigit() else taxon.strip()
            for taxon in taxa.split(",")
        ]
        # get the filename
        # by default we'll just use the inputs
        if to is None:
            to = Path(",".join([str(t) for t in taxon_ids]) + ".tab.gz")
        elif str(to).startswith("."):
            to = Path(",".join([str(t) for t in taxon_ids]) + str(to))
        to.parent.mkdir(exist_ok=True, parents=True)
        # TODO: this is quite inefficient
        # we're potentially reading in the vertebrata file multiple times
        # we could instead read it in, then concatenate the matching subtrees
        # however, this is moderately efficient if you ask for, e.g., Mammalia and Plantae
        # then it'll download Plantae but just get Mammalia from the resource-file Vertebrata
        logger.error(to)
        taxes = []
        for taxon in taxon_ids:
            tax = TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(taxon)
            taxes.append(tax.to_df())
        final_tax = TaxonomyDf(pd.concat(taxes, ignore_index=True))
        final_tax = final_tax.drop_duplicates().sort_values("taxon")
        # if it's text, just write one taxon ID per line
        is_text = any((to.name.endswith(".txt" + c) for c in {"", ".gz", ".zip", ".xz", ".bz2"}))
        if is_text:
            final_tax = TypedDfs.wrap(final_tax[["taxon"]])
        # write the file
        final_tax.write_file(to)

    @staticmethod
    def dl_tax(
        taxon: int = typer.Argument(None, help="The **ID** of the UniProt taxon"),
    ) -> None:
        """
        Preps a new taxonomy file for use in mandos.
        Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
        Otherwise, downloads a tab-separated file from UniProt.
        (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
        Then applies fixes and reduces the file size, creating a new file alongside.
        Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.
        """
        TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(taxon)


def _init_commands():
    # Oh dear this is a nightmare
    # it's really hard to create typer commands with dynamically configured params --
    # we really need to rely on its inferring of params
    # that makes this really hard to do well
    for entry in Entries:

        info = CommandInfo(entry.cmd(), callback=entry.run)
        cli.registered_commands.append(info)
        # print(f"Registered {entry.cmd()} to {entry}")
        setattr(Commands, entry.cmd(), entry.run)

    cli.registered_commands.extend(
        [
            CommandInfo("@search", callback=Commands.search),
            CommandInfo("@tax-tree", callback=Commands.build_taxonomy),
            CommandInfo("@tax-dl", callback=Commands.dl_tax, hidden=True),
        ]
    )


_init_commands()


class MandosCli:
    """
    Global entry point for various stuff. For import by consumers.
    """

    settings = MANDOS_SETTINGS
    logger = logger
    logging = MandosLogging
    main = cli
    commands = Commands

    @classmethod
    def init(cls) -> Type[MandosCli]:
        MandosLogging.init()
        Apis.set_default()
        return cls


if __name__ == "__main__":
    MandosCli.init().main()


__all__ = ["MandosCli"]
