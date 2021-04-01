"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from mandos import logger
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy import TaxonomyDf
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.entries.entries import Entries, _Typer
from mandos.entries.api_singletons import Apis
from mandos.entries.multi_searches import MultiSearch
from mandos.entries.searcher import SearcherUtils

# IMPORTANT!
Apis.set_default()
cli = typer.Typer()
# _old_wrap_text = copy(click.formatting.wrap_text)
# def _new_wrap_text(
#    text, width=100, initial_indent="", subsequent_indent="", preserve_paragraphs=False
# ):
#    return _old_wrap_text(text, 100, initial_indent, subsequent_indent, preserve_paragraphs)
# click.formatting.wrap_text = _new_wrap_text


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
    def build_taxonomy(
        taxa: str = typer.Argument(
            None,
            help="""
            UniProt taxon ID or scientific name, comma-separated.
            Scientific names are only permitted for subsets of vertebrata.
        """,
        ),
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
            int(taxon.strip()) if taxon.isdigit() else taxon.strip() for taxon in taxa.split(",")
        ]
        # get the filename
        # by default we'll just use the inputs
        default_path = Path(",".join([str(t).strip() for t in taxa]) + ".tab.gz")
        if to is None:
            to = default_path
        elif str(to).startswith("."):
            to = default_path.with_suffix(str(to))
        to.parent.mkdir(exist_ok=True, parents=True)
        # TODO: this is quite inefficient
        # we're potentially reading in the vertebrata file multiple times
        # we could instead read it in, then concatenate the matching subtrees
        # however, this is moderately efficient if you ask for, e.g., Mammalia and Plantae
        # then it'll download Plantae but just get Mammalia from the resource-file Vertebrata
        taxes = []
        for taxon in taxon_ids:
            tax = TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(taxon)
            taxes.append(tax.to_df())
        final_tax = TaxonomyDf.concat(taxes, ignore_index=True)
        final_tax = final_tax.drop_duplicates().sort_values("taxon")
        final_tax.write_file(to)

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
        CommandInfo("@tax-tree", callback=Commands.build_taxonomy),
        CommandInfo("@tax-dl", callback=Commands.dl_tax, hidden=True),
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
    logger.addHandler(handler)
    # log_factory = PrettyRecordFactory(10, 12, 5, width=100, symbols=True).modifying(logger)
    # good start; can be changed
    root.setLevel(logging.WARNING)
    logger.setLevel(logging.INFO)
    cli()


__all__ = ["Commands"]
