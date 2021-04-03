"""
Caching.
"""

from __future__ import annotations

import abc
import shutil
from datetime import datetime
from pathlib import Path
from typing import Union

import pandas as pd
import requests
from pocketutils.core.hashers import Hasher

from mandos import logger
from mandos.model import MandosResources
from mandos.model.taxonomy import Taxonomy
from mandos.model.settings import MANDOS_SETTINGS

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

    def load_by_name(self, taxon: str) -> Taxonomy:
        vertebrata = Taxonomy.from_path(MandosResources.VERTEBRATA_PATH)
        only = vertebrata.req_only_by_name(taxon)
        return vertebrata.subtree(only.id)

    def load(self, taxon: Union[int, str]) -> Taxonomy:
        """
        Tries, in order:

            1. A cached file exactly matching the taxon ID
            2. A taxon ID under vertebrata
            3. The UNIQUE name of a taxon under vertebrata
            4. Downloads the taxonomy with the specified ID
        """
        tree = self._load(taxon)
        logger.info(f"Taxonomy has {len(tree)} taxa with {len(tree.roots)} roots")
        return tree

    def _load(self, taxon: Union[int, str]) -> Taxonomy:
        if isinstance(taxon, str) and taxon.isdigit():
            taxon = int(taxon)
        if isinstance(taxon, int):
            path = self._resolve_non_vertebrate_final(taxon)
            if path.exists():
                return Taxonomy.from_path(path)
        vertebrata = Taxonomy.from_path(MandosResources.VERTEBRATA_PATH)
        if isinstance(taxon, int) and taxon in vertebrata:
            logger.info(f"Taxon {taxon} found in the vertebrata cache")
            return vertebrata.subtree(taxon)
        elif isinstance(taxon, str):
            match = vertebrata.req_only_by_name(taxon).id
            logger.info(f"Taxon {match} found in the vertebrata cache")
            return vertebrata.subtree(match)
        if isinstance(taxon, int):
            raw_path = self._resolve_non_vertebrate_raw(taxon)
            if raw_path.exists():
                logger.warning(
                    f"Raw download for taxonomy of {taxon} found at {raw_path}. Converting it."
                )
                # getting the mod date because creation dates are iffy cross-platform
                # (in fact the Linux kernel doesn't bother to expose them)
                when = datetime.fromtimestamp(raw_path.stat().st_mtime).strftime("%Y-%m-%d")
                logger.warn(f"It may be out of date. (File mod date: {when})")
            else:
                logger.warning(
                    f"Downloading new taxonomy file for taxon {taxon}. This may take a while."
                )
                self._download(raw_path, taxon)
            self._fix(raw_path, taxon, path)
            logger.warning(f"Cached taxonomy at {path}.")
            return Taxonomy.from_path(path)
        else:
            raise LookupError(f"Could not find taxon {taxon}; try passing an ID instead")

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
        # so, we'll add it in (in ``df.append`` below)
        df = pd.read_file(raw_path)
        # find the scientific name of the parent
        scientific_name = self._determine_name(df, taxon)
        # now fix the columns
        df = df[["Taxon", "Scientific name", "Common name", "Parent"]]
        df.columns = ["taxon", "scientific_name", "common_name", "parent"]
        # now add the ancestor back in
        df = df.append(
            pd.Series(dict(taxon=taxon, scientific_name=scientific_name, parent=0)),
            ignore_index=True,
        )
        # write it to a csv.gz
        df["parent"] = df["parent"].astype(int)
        df.write_file(final_path)

    def _determine_name(self, df: pd.DataFrame, taxon: int) -> str:
        got = df[df["Parent"] == taxon]
        if len(got) == 0:
            raise ValueError(f"Could not infer scientific name for {taxon}")
        z = str(list(got["Lineage"])[0])
        return z.split("; ")[-1].strip()


class FixedTaxonomyFactory(TaxonomyFactory):
    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def load(self, taxon: Union[int, str]) -> Taxonomy:
        if isinstance(taxon, str):
            taxon = self._tax.req_only_by_name(taxon).id
        return self._tax.subtree(taxon)


class FixedFileTaxonomyFactory(TaxonomyFactory):
    def __init__(self, path: Path):
        self._path = path

    def load(self, taxon: Union[int, str]) -> Taxonomy:
        taxonomy = Taxonomy.from_path(self._path)
        if isinstance(taxon, str):
            taxon = taxonomy.req_only_by_name(taxon).id
        return taxonomy.subtree(taxon)


class CacheDirTaxonomyCache(UniprotTaxonomyCache):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    def _resolve_non_vertebrate_final(self, taxon: int) -> Path:
        return self._get_resource(MANDOS_SETTINGS.taxonomy_filename_format.format(taxon))

    def _resolve_non_vertebrate_raw(self, taxon: int) -> Path:
        # this is what is downloaded from PubChem
        # the filename is the same
        return self._get_resource(f"taxonomy-ancestor_{taxon}.tab.gz")

    def _get_resource(self, *nodes: Union[Path, str]) -> Path:
        path = MandosResources.path(*nodes)
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
        return CacheDirTaxonomyCache(MandosResources.VERTEBRATA_PATH)

    @classmethod
    def from_uniprot(cls, cache_dir: Path) -> TaxonomyFactory:
        return CacheDirTaxonomyCache(cache_dir)

    @classmethod
    def from_fixed_file(cls, cache_dir: Path) -> TaxonomyFactory:
        return FixedFileTaxonomyFactory(cache_dir)


__all__ = ["TaxonomyFactory", "TaxonomyFactories"]
