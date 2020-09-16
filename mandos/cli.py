"""
Command-line interface for mandos.
"""

from __future__ import annotations

import enum
import logging
import shutil
from pathlib import Path
from typing import Optional, Sequence, Type, Union

import pandas as pd
import requests
import typer
from chembl_webresource_client.new_client import new_client as Chembl

from mandos import get_resource
from mandos.activity import ActivitySearch
from mandos.atcs import AtcSearch
from mandos.mechanisms import MechanismSearch
from mandos.model import ChemblApi, Search
from mandos.model.taxonomy import Taxonomy

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


def get_cache_resource(*nodes: Union[Path, str]) -> Path:
    """"""
    cache = Path.home() / ".mandos"
    cache.mkdir(parents=True, exist_ok=True)
    return Path(cache, *nodes)


class Commands:
    """
    Entry points for mandos.
    """

    @staticmethod
    @cli.command()
    def search(
        what: What,
        inchis_path: Optional[Path] = None,
        write_path: Optional[Path] = None,
        tax: int = 117571,
    ) -> None:
        """
        Process data.

        Args:
            what: Activity / ATCs / mechanisms / etc.
            inchis_path: Path to file containing one InChI per line
            write_path: Path of a CSV file to write
            tax: Restrict to organisms under this UniProt tax ID or scientific name.
                        UniProt uses a cladastic tree.
                        117571 (Euteleostomi, 430 Mya) is a good choice.
                        If the taxon is outside of 7742 (Vertebrata, 525 Mya),
                        a new file will be downloaded from UniProt and cached.
        """
        compounds = inchis_path.read_text(encoding="utf8").splitlines()
        df = Commands.search_for(what, compounds, tax=tax)
        df.to_csv(write_path)

    @staticmethod
    def search_for(
        what: What, compounds: Sequence[str], tax: Union[int, str] = None
    ) -> pd.DataFrame:
        """

        Args:
            what:
            compounds:
            tax:

        Returns:

        """
        tax = Taxonomy.from_df(Commands.process_tax(tax))
        compounds = list(compounds)
        api = ChemblApi.wrap(Chembl)
        hits = what.clazz(api, tax).find_all(compounds)
        df = pd.DataFrame(
            [pd.Series({f: getattr(h, f) for f in what.clazz.hit_fields()}) for h in hits]
        )
        return df

    @staticmethod
    @cli.command()
    def process_tax(taxon: int) -> Path:
        """
        Preps a new taxonomy file for use in mandos.
        Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
        Otherwise, downloads a tab-separated file from UniProt.
        (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
        Then applies fixes and reduces the file size, creating a new file alongside.
        Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.

        Args:
            taxon: The **ID** of the UniProt taxon

        Returns:
            The final path to the csv.gz file

        """
        # check whether it exists
        if Commands._find_tax_file(taxon):
            # man, this would be a great use of the new Python 3.9 guard statement
            return Commands._find_tax_file(taxon)
        # download it
        raw_path = get_cache_resource(f"taxonomy-ancestor_{taxon}.tab.gz")
        output_path = get_cache_resource("taxonomy", f"{taxon}.tab.gz")
        Commands._download_tax_file(taxon, raw_path)
        # now process it!
        # unfortunately it won't include an entry for the root ancestor (`taxon`)
        # so, we'll add it in
        df = pd.read_csv(raw_path, sep="\t")
        # find the scientific name of the parent
        got = df[df["Parent"] == taxon]
        if len(got) == 0:
            raise ValueError(f"Could not infer scientific name for {taxon}")
        scientific_name = got["Lineage"][0].split("; ")[-1].strip()
        # now fix the columns
        df = df[["Taxon", "Scientific name", "Parent"]]
        df.columns = ["taxon", "scientific_name", "parent"]
        # now add the ancestor back in
        df = df.append(
            pd.Series(dict(taxon=taxon, scientific_name=scientific_name, parent=None)),
            ignore_index=True,
        )
        # write it to a csv.gz
        df["parent"] = df["parent"].astype(str).str.rstrip(".0")
        df.to_csv(output_path, index=False, sep="\t")
        return output_path

    @staticmethod
    def _find_tax_file(taxon: int) -> Optional[Path]:
        path = get_resource(f"{taxon}.tab")
        if not path.exists():
            path = get_cache_resource("taxonomy", f"{taxon}.tab")
        if path.exists():
            logger.info(f"Found {taxon} at {path}")
            return get_resource(path)
        return None

    @staticmethod
    def _download_tax_file(taxon: int, path: Path) -> None:
        # https://uniprot.org/taxonomy/?query=ancestor:7742&format=tab&force=true&columns=id&compress=yes
        url = f"https://uniprot.org/taxonomy/?query=ancestor:{taxon}&format=tab&force=true&columns=id&compress=yes"
        with requests.get(url, stream=True) as r:
            with open(str(path), "wb") as f:
                shutil.copyfileobj(r.raw, f)


if __name__ == "__main__":
    cli()
