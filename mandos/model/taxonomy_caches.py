"""
Caching.
"""

from __future__ import annotations

import abc
import shutil
from pathlib import Path
from typing import Collection, Iterable, Mapping, Optional, Set, Union

import decorateme
import pandas as pd
import requests
from pocketutils.core.exceptions import XValueError
from typeddfs import Checksums, TypedDfs

from mandos.model.settings import SETTINGS
from mandos.model.taxonomy import Taxonomy, TaxonomyDf
from mandos.model.utils.globals import Globals
from mandos.model.utils.resources import MandosResources
from mandos.model.utils.setup import logger


@decorateme.auto_repr_str()
class TaxonomyFactory(metaclass=abc.ABCMeta):
    def load(self, taxon: Union[int, str]) -> Taxonomy:
        raise NotImplementedError()


class CachedTaxonomyCache(TaxonomyFactory, metaclass=abc.ABCMeta):
    """
    Preps a new taxonomy file for use in mandos.
    Just returns if a corresponding file already exists in the resources dir or mandos cache (``~/.mandos``).
    Otherwise, downloads a tab-separated file from UniProt.
    (To find manually, follow the ``All lower taxonomy nodes`` link and click ``Download``.)
    Then applies fixes and reduces the file size, creating a new file alongside.
    Puts both the raw data and fixed data in the cache under ``~/.mandos/taxonomy/``.
    """

    def __init__(self, *, cache_dir: Path = SETTINGS.taxonomy_cache_path, local_only: bool):
        self.cache_dir = cache_dir
        self.local_only = local_only

    def load(self, taxon: Union[int, str]) -> Taxonomy:
        """
        Tries, in order:

            1. A cached file exactly matching the taxon ID
            2. A taxon ID under vertebrata
            3. The UNIQUE name of a taxon under vertebrata
            4. Downloads the taxonomy with the specified ID
        """
        tree = self.load_exact(taxon)
        if tree is None:
            vert = self.load_vertebrate(Globals.vertebrata)
            if taxon in vert:
                tree = vert.subtrees_by_ids_or_names(taxon)
            else:
                logger.info(f"Taxon {taxon} found in the vertebrata cache")
                tree = self._load_or_dl(taxon)
        logger.info(f"Taxonomy has {len(tree)} taxa with {len(tree.roots)} roots")
        return tree

    def load_exact(self, taxon: int) -> Optional[Taxonomy]:
        path = self._resolve_non_vertebrate_final(taxon)
        if (self._check_has(taxon, path) or self.local_only) and path.exists():
            return Taxonomy.from_path(path)
        return None

    def load_vertebrate(self, taxon: Union[int, str]) -> Optional[Taxonomy]:
        vertebrata = self._load_or_dl(Globals.vertebrata)
        vertebrate = vertebrata.subtrees_by_ids_or_names([taxon])
        return vertebrate if vertebrate.n_taxa() > 0 else None

    def _check_has(self, taxon: Union[str, int], path: Path) -> bool:
        if path.exists():
            return not MandosResources.check_expired(
                path,
                max_sec=SETTINGS.taxon_expire_sec,
                what=f"Cached taxa under {taxon} ({path})",
            )
        return False

    def _load_or_dl(self, taxon: Union[int, str]) -> Taxonomy:
        path = self._resolve_non_vertebrate_final(taxon)
        raw_path = self._resolve_non_vertebrate_raw(taxon)
        if self._check_has(taxon, path) or self.local_only:
            return Taxonomy.from_path(path)
        else:
            # raise AssertionError(str(taxon))  # TODO
            logger.notice(f"Downloading new taxonomy file for taxon {taxon}")
            self._download_raw(raw_path, taxon)
            path = self._resolve_non_vertebrate_final(taxon)
            df = self._fix(raw_path, taxon, path)
            logger.notice(f"Cached taxonomy at {path} .")
            return Taxonomy.from_df(df)

    def rebuild(self, *taxa: int, replace: bool) -> None:
        if self.local_only:
            logger.error(f"Cannot rebuild -- local_only is set")
        for taxon in taxa:
            path = self.resolve_path(taxon)
            if replace or not path.exists():
                self.delete_exact(taxon)
                self._load_or_dl(taxon)
                logger.notice(f"Regenerated {taxon} taxonomy")

    def delete_exact(self, taxon: int) -> None:
        raw = self._resolve_non_vertebrate_raw(taxon)
        raw.unlink(missing_ok=True)
        p = self._resolve_non_vertebrate_raw(taxon)
        if p.exists():
            p.unlink()
            logger.warning(f"Deleted cached taxonomy file {p}")
        # delete either way:
        checksum_file = Checksums().get_filesum_of_file(p)
        checksum_file.unlink(missing_ok=True)

    def resolve_path(self, taxon: int) -> Path:
        return self._resolve_non_vertebrate_final(taxon)

    def _resolve_non_vertebrate_final(self, taxon: int) -> Path:
        return self._get_resource(f"{taxon}{SETTINGS.archive_filename_suffix}")

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

    def _download_raw(self, raw_path: Path, taxon: int) -> None:
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
        logger.debug("Fixing raw taxonomy download")
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
    """
    Mostly for testing.
    """

    def __init__(self, tax: Taxonomy):
        self._tax = tax

    def load(self, taxon: Union[int, str]) -> Taxonomy:
        if isinstance(taxon, str):
            taxon = self._tax.req_only_by_name(taxon).id
        return self._tax.subtree(taxon)


class TaxonomyFactories:
    """
    Collection of static factory methods.
    """

    @classmethod
    def list_cached_files(cls) -> Mapping[int, Path]:
        suffix = SETTINGS.archive_filename_suffix
        return {
            int(p.scientific_name.replace(suffix, "")): p
            for p in SETTINGS.taxonomy_cache_path.iterdir()
            if p.suffix.endswith(suffix)
        }

    @classmethod
    def main(
        cls,
        cache_dir: Path = SETTINGS.taxonomy_cache_path,
        local_only: bool = False,
    ):
        return CachedTaxonomyCache(local_only=local_only, cache_dir=cache_dir)

    @classmethod
    def get_smart_taxonomy(
        cls,
        *,
        allow: Iterable[Union[int, str]],
        forbid: Iterable[Union[int, str]],
        ancestors: Union[int, Collection[int]] = Globals.cellular_taxon,
        cache_dir: Path = SETTINGS.taxonomy_cache_path,
        local_only: bool,
    ) -> Taxonomy:
        cache = CachedTaxonomyCache(local_only=local_only, cache_dir=cache_dir)
        vertebrata = cache.load_vertebrate(Globals.vertebrata)
        return vertebrata
        # TODO:
        # return vertebrata.subtrees_by_ids_or_names(allow)
        # .exclude_subtrees_by_ids_or_names(forbid)
        vertebrates: Set[Union[int, str]] = {t for t in allow if t in vertebrata}
        invertebrates: Set[Union[int, str]] = {t for t in allow if t not in vertebrata}
        trees: Set[Taxonomy] = {cache.load(t) for t in vertebrates}
        if len(invertebrates) > 0:
            logger.debug(
                f"{len(invertebrates)} invertebrate taxa found with {len(ancestors)} ancestors"
            )
            if len(ancestors) == 0:
                new = {cache.load(t) for t in invertebrates}
            else:
                new = Taxonomy.from_trees({cache.load(t) for t in ancestors})
            trees.add(new.subtrees_by_ids_or_names(invertebrates))
            logger.debug(f"Added {len(invertebrates)} invertebrate taxa into taxonomy")
        return Taxonomy.from_trees(trees).exclude_subtrees_by_ids_or_names(forbid)


__all__ = ["TaxonomyFactory", "TaxonomyFactories"]
