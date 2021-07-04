"""
Caching.
"""

from __future__ import annotations

import abc
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union

import pandas as pd
import requests
from pocketutils.core.hashers import Hasher

from mandos import logger
from mandos.model import MandosResources
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy import Taxonomy

hasher = Hasher("sha1")


class TaxonomyFactory(metaclass=abc.ABCMeta):
    def load(self, taxon: Union[int, str]) -> Taxonomy:
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
        exact = self.load_vertebrate(taxon)
        if exact is not None:
            logger.info(f"Taxon {taxon} found in cached file")
            return exact
        vertebrate = self.load_vertebrate(taxon)
        if vertebrate is not None:
            logger.info(f"Taxon {taxon} found in the vertebrata cache")
            return vertebrate
        raise LookupError(f"Could not find taxon {taxon}; try passing an ID instead")

    def load_exact(self, taxon: int) -> Optional[Taxonomy]:
        path = self._resolve_non_vertebrate_final(taxon)
        return Taxonomy.from_path(path) if path.exists() else None

    def load_vertebrate(self, taxon: Union[int, str]) -> Optional[Taxonomy]:
        vertebrata = Taxonomy.from_path(MandosResources.VERTEBRATA_PATH)
        vertebrate = vertebrata.subtrees_by_ids_or_names([taxon])
        return vertebrate if vertebrate.n_taxa() > 0 else None

    def load_dl(self, taxon: Union[int, str]) -> Taxonomy:
        raw_path = self._resolve_non_vertebrate_raw(taxon)
        if raw_path.exists():
            logger.warning(f"Converting temp file for taxon {taxon} at {raw_path} .")
            # getting the mod date because creation dates are iffy cross-platform
            # (in fact the Linux kernel doesn't bother to expose them)
            when = datetime.fromtimestamp(raw_path.stat().st_mtime).strftime("%Y-%m-%d")
            logger.warning(f"It may be out of date. (File mod date: {when})")
        else:
            logger.info(f"Downloading new taxonomy file for taxon {taxon} .")
            self._download(raw_path, taxon)
        path = self._resolve_non_vertebrate_final(taxon)
        self._fix(raw_path, taxon, path)
        logger.info(f"Cached taxonomy at {path} .")
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

    def _fix(self, raw_path: Path, taxon: int, final_path: Path) -> None:
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
        # write it to a feather / csv / whatever
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
        return self._get_resource(f"taxonomy-ancestor_{taxon}.feather")

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
    def from_vertebrata(cls) -> UniprotTaxonomyCache:
        return CacheDirTaxonomyCache(MandosResources.VERTEBRATA_PATH)

    @classmethod
    def from_uniprot(
        cls, cache_dir: Path = MANDOS_SETTINGS.taxonomy_cache_path
    ) -> UniprotTaxonomyCache:
        return CacheDirTaxonomyCache(cache_dir)

    @classmethod
    def from_fixed_file(
        cls, cache_dir: Path = MANDOS_SETTINGS.taxonomy_cache_path
    ) -> TaxonomyFactory:
        return FixedFileTaxonomyFactory(cache_dir)

    @classmethod
    def get_smart_taxonomy(
        cls,
        allow: Iterable[Union[int, str]],
        forbid: Iterable[Union[int, str]],
        cache_dir: Path = MANDOS_SETTINGS.taxonomy_cache_path,
    ) -> Taxonomy:
        vertebrata = cls.from_vertebrata().load(7742)
        vertebrates = vertebrata.subtrees_by_ids_or_names(allow)
        invertebrates: Sequence[Taxonomy] = [
            cls.from_uniprot(cache_dir).load(taxon)
            for taxon in allow
            if vertebrata.get_by_id_or_name(taxon) is None
        ]
        my_tax = Taxonomy.from_trees([vertebrates, *invertebrates])
        my_tax = my_tax.exclude_subtrees_by_ids_or_names(forbid)
        return my_tax


__all__ = ["TaxonomyFactory", "TaxonomyFactories"]
