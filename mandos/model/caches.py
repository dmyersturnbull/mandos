"""
Caching.
"""

from __future__ import annotations

import abc
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


class TaxonomyFactory(metaclass=abc.ABCMeta):
    def load(self, taxon: int) -> Taxonomy:
        raise NotImplementedError()


class UniprotTaxonomyCache(TaxonomyFactory, metaclass=abc.ABCMeta):
    """
    Preps a new taxonomy file for use in mandos.
    Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
    Otherwise, downloads a tab-separated file from UniProt.
    (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
    Then applies fixes and reduces the file size, creating a new file alongside.
    Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.
    """

    def load(self, taxon: int) -> Taxonomy:
        path = self._resolve_non_vertebrate_final(taxon)
        if path.exists():
            return Taxonomy.from_path(path)
        vertebrata = Taxonomy.from_path(get_resource("7742.tab.gz"))
        if taxon in vertebrata:
            return vertebrata.subtree(taxon)
        raw_path = self._resolve_non_vertebrate_raw(taxon)
        if not raw_path.exists():
            self._download(raw_path, taxon)
            self._fix(raw_path, taxon, path)
        return Taxonomy.from_path(path)

    def _resolve_non_vertebrate_final(self, taxon: int) -> Path:
        raise NotImplementedError()

    def _resolve_non_vertebrate_raw(self, taxon: int) -> Path:
        raise NotImplementedError()

    def _download(self, raw_path: Path, taxon: int) -> None:
        # this is faster and safer than using pd.read_csv(url)
        # https://uniprot.org/taxonomy/?query=ancestor:7742&format=tab&force=true&columns=id&compress=yes
        url = f"https://uniprot.org/taxonomy/?query=ancestor:{taxon}&format=tab&force=true&columns=id&compress=yes"
        with requests.get(url, stream=True) as r:
            with raw_path.open("wb") as f:
                shutil.copyfileobj(r.raw, f)
        hasher.to_write(raw_path).write()

    def _fix(self, raw_path: Path, taxon: int, final_path: Path):
        # now process it!
        # unfortunately it won't include an entry for the root ancestor (`taxon`)
        # so, we'll add it in
        df = pd.read_csv(raw_path, sep="\t")
        # find the scientific name of the parent
        scientific_name = self._determine_name(df, taxon)
        # now fix the columns
        df = df[["Taxon", "Scientific name", "Parent"]]
        df.columns = ["taxon", "scientific_name", "parent"]
        # now add the ancestor back in
        df = df.append(
            pd.Series(dict(taxon=taxon, scientific_name=scientific_name, parent=0)),
            ignore_index=True,
        )
        # write it to a csv.gz
        df["parent"] = df["parent"].astype(int)
        df.to_csv(final_path, index=False, sep="\t")

    def _determine_name(self, df: pd.DataFrame, taxon: int) -> str:
        got = df[df["Parent"] == taxon]
        if len(got) == 0:
            raise ValueError(f"Could not infer scientific name for {taxon}")
        z = str(list(got["Lineage"])[0])
        return z.split("; ")[-1].strip()


class FixedTaxonomyFactory(TaxonomyFactory):
    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def load(self, taxon: int) -> Taxonomy:
        return self._tax.subtree(taxon)


class FixedFileTaxonomyFactory(TaxonomyFactory):
    def __init__(self, path: Path):
        self._path = path

    def load(self, taxon: int) -> Taxonomy:
        return Taxonomy.from_path(self._path).subtree(taxon)


class CacheDirTaxonomyCache(UniprotTaxonomyCache):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    def _resolve_non_vertebrate_final(self, taxon: int) -> Path:
        return self._get_resource(f"{taxon}.tab.gz")

    def _resolve_non_vertebrate_raw(self, taxon: int) -> Path:
        return self._get_resource(f"taxonomy-ancestor_{taxon}.tab.gz")

    def _get_resource(self, *nodes: Union[Path, str]) -> Path:
        path = get_resource(*nodes)
        if path.exists():
            return path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        return Path(self.cache_dir, *nodes)


class TaxonomyFactories:
    """
    Collection of static factory methods.
    """

    @classmethod
    def from_vertebrata(cls) -> TaxonomyFactory:
        return CacheDirTaxonomyCache(get_resource("7742.tab.gz"))

    @classmethod
    def from_uniprot(cls, cache_dir: Path) -> TaxonomyFactory:
        return CacheDirTaxonomyCache(cache_dir)

    @classmethod
    def from_fixed_file(cls, cache_dir: Path) -> TaxonomyFactory:
        return FixedFileTaxonomyFactory(cache_dir)


__all__ = ["TaxonomyFactory", "TaxonomyFactories"]
