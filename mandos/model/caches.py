"""
Caching.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Union

import pandas as pd
import requests
from pocketutils.core.hashers import Hasher

from mandos import get_resource
from mandos.model.taxonomy import Taxonomy

logger = logging.getLogger(__package__)
hasher = Hasher("sha1")


def get_cache_resource(*nodes: Union[Path, str]) -> Path:
    """"""
    path = get_resource(*nodes)
    if path.exists():
        return path
    cache = Path.home() / ".mandos"
    cache.mkdir(parents=True, exist_ok=True)
    return Path(cache, *nodes)


class TaxonomyCache:
    def __init__(self, taxon: int):
        self.taxon = taxon

    @property
    def exists(self) -> bool:
        return self.path.exists() and self.raw_path.exists()

    @property
    def path(self) -> Path:
        return get_cache_resource(f"{self.taxon}.tab.gz")

    @property
    def raw_path(self) -> Path:
        return get_cache_resource(f"taxonomy-ancestor_{self.taxon}.tab.gz")

    def load(self) -> Taxonomy:
        """
        Preps a new taxonomy file for use in mandos.
        Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
        Otherwise, downloads a tab-separated file from UniProt.
        (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
        Then applies fixes and reduces the file size, creating a new file alongside.
        Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.
        """
        # check whether it exists
        if not self.exists:
            if not self.raw_path.exists():
                self._download()
            self._fix()
        df = pd.read_csv(self.path, sep="\t", header=0)
        return Taxonomy.from_df(df)

    def _fix(self):
        # now process it!
        # unfortunately it won't include an entry for the root ancestor (`taxon`)
        # so, we'll add it in
        raw_path = self.raw_path
        df = pd.read_csv(raw_path, sep="\t")
        # find the scientific name of the parent
        got = df[df["Parent"] == self.taxon]
        if len(got) == 0:
            raise ValueError(f"Could not infer scientific name for {self.taxon}")
        scientific_name = got["Lineage"][0].split("; ")[-1].strip()
        # now fix the columns
        df = df[["Taxon", "Scientific name", "Parent"]]
        df.columns = ["taxon", "scientific_name", "parent"]
        # now add the ancestor back in
        df = df.append(
            pd.Series(dict(taxon=self.taxon, scientific_name=scientific_name, parent=None)),
            ignore_index=True,
        )
        # write it to a csv.gz
        df["parent"] = df["parent"].astype(str).str.rstrip(".0")
        df.to_csv(self.path, index=False, sep="\t")

    def _download(self) -> None:
        raw_path = self.raw_path
        # this is faster and safer than using pd.read_csv(url)
        taxon = self.taxon
        # https://uniprot.org/taxonomy/?query=ancestor:7742&format=tab&force=true&columns=id&compress=yes
        url = f"https://uniprot.org/taxonomy/?query=ancestor:{taxon}&format=tab&force=true&columns=id&compress=yes"
        with requests.get(url, stream=True) as r:
            with raw_path.open("wb") as f:
                shutil.copyfileobj(r.raw, f)
        hasher.to_write(raw_path).write()


__all__ = ["TaxonomyCache"]
