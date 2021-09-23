"""
Caching.
"""

from __future__ import annotations

import abc
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union, Mapping

import pandas as pd
import requests
from pocketutils.core.exceptions import LookupFailedError, XValueError
from typeddfs import TypedDfs

from mandos.model.utils.setup import logger
from mandos.model.utils.resources import MandosResources
from mandos.model.settings import MANDOS_SETTINGS
from mandos.model.taxonomy import Taxonomy, TaxonomyDf


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
        exact = self.load_exact(taxon)
        if exact is not None:
            logger.info(f"Taxon {taxon} found in cached file")
            return exact
        vertebrate = self.load_vertebrate(taxon)
        if vertebrate is not None:
            logger.info(f"Taxon {taxon} found in the vertebrata cache")
            return vertebrate
        raise LookupFailedError(f"Could not find taxon {taxon}; try passing an ID instead")

    def load_exact(self, taxon: int) -> Optional[Taxonomy]:
        path = self._resolve_non_vertebrate_final(taxon)
        return Taxonomy.from_path(path) if path.exists() else None

    def load_vertebrate(self, taxon: Union[int, str]) -> Optional[Taxonomy]:
        vertebrata = self.load_dl(7742)
        vertebrate = vertebrata.subtrees_by_ids_or_names([taxon])
        return vertebrate if vertebrate.n_taxa() > 0 else None

    def load_dl(self, taxon: Union[int, str]) -> Taxonomy:
        path = self._resolve_non_vertebrate_final(taxon)
        raw_path = self._resolve_non_vertebrate_raw(taxon)
        if path.exists():
            # getting the mod date because creation dates are iffy cross-platform
            # (in fact the Linux kernel doesn't bother to expose them)
            when = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            logger.warning(f"It may be out of date. (File mod date: {when})")
            return Taxonomy.from_path(path)
        else:
            logger.notice(f"Downloading new taxonomy file for taxon {taxon} .")
            self._download(raw_path, taxon)
            path = self._resolve_non_vertebrate_final(taxon)
            df = self._fix(raw_path, taxon, path)
            logger.notice(f"Cached taxonomy at {path} .")
            return df

    def rebuild_vertebrata(self) -> None:
        self.delete_exact(7742)
        self.load_dl(7742)
        logger.notice(f"Regenerated vertebrata tree")

    def delete_exact(self, taxon: int) -> None:
        raw = self._resolve_non_vertebrate_raw(taxon)
        raw.unlink(missing_ok=True)
        p = self._resolve_non_vertebrate_raw(taxon)
        if p.exists():
            p.unlink()
            logger.warning(f"Deleted cached taxonomy file {p}")
        # delete either way:
        MandosResources.hasher.any(p).hash_path.unlink(missing_ok=True)

    def resolve_path(self, taxon: int) -> Path:
        return self._resolve_non_vertebrate_final(taxon)

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

    def _fix(self, raw_path: Path, taxon: int, final_path: Path) -> TaxonomyDf:
        # now process it!
        # unfortunately it won't include an entry for the root ancestor (`taxon`)
        # so, we'll add it in (in ``df.append`` below)
        # noinspection PyPep8Naming
        raw_type = TypedDfs.untyped("Raw")
        df = raw_type.read_file(raw_path)
        # find the scientific name of the parent
        scientific_name = self._determine_name(df, taxon)
        # now fix the columns
        df = df[["Taxon", "Mnemonic", "Scientific name", "Common name", "Parent"]]
        df.columns = ["taxon", "mnemonic", "scientific_name", "common_name", "parent"]
        # now add the ancestor back in
        df = df.append(
            pd.Series(dict(taxon=taxon, scientific_name=scientific_name, parent=0)),
            ignore_index=True,
        )
        df["parent"] = df["parent"].fillna(0).astype(int)
        # write it to a feather / csv / whatever
        df = TaxonomyDf.convert(df)
        df.write_file(final_path, dir_hash=True)
        raw_path.unlink()
        return df

    def _determine_name(self, df: pd.DataFrame, taxon: int) -> str:
        got = df[df["Parent"] == taxon]
        if len(got) == 0:
            raise XValueError(f"Could not infer scientific name for {taxon}")
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
        return self._get_resource(f"{taxon}{MANDOS_SETTINGS.archive_filename_suffix}")

    def _resolve_non_vertebrate_raw(self, taxon: int) -> Path:
        # this is what is downloaded from PubChem
        # the filename is the same
        return self._get_resource(f"taxonomy-ancestor_{taxon}.tsv.gz")

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
    def list_cached_files(cls) -> Mapping[int, Path]:
        suffix = MANDOS_SETTINGS.archive_filename_suffix
        return {
            int(p.scientific_name.replace(suffix, "")): p
            for p in MANDOS_SETTINGS.taxonomy_cache_path.iterdir()
            if p.suffix.endswith(suffix)
        }

    @classmethod
    def from_vertebrata(cls) -> FixedFileTaxonomyFactory:
        path = CacheDirTaxonomyCache(MANDOS_SETTINGS.taxonomy_cache_path).resolve_path(7742)
        return FixedFileTaxonomyFactory(path)

    @classmethod
    def from_uniprot(
        cls, cache_dir: Path = MANDOS_SETTINGS.taxonomy_cache_path
    ) -> UniprotTaxonomyCache:
        return CacheDirTaxonomyCache(cache_dir)

    @classmethod
    def from_fixed_file(cls, path: Path) -> TaxonomyFactory:
        return FixedFileTaxonomyFactory(path)

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
