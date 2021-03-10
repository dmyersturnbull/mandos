"""
Command-line interface for mandos.
"""

from __future__ import annotations

import logging
from pathlib import Path, PurePath
from typing import Sequence, Set, Optional
from typing import Tuple as Tup
from typing import Type, Union

import pandas as pd
import typer
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.model.chembl_api import ChemblApi
from mandos.model.chembl_support.chembl_targets import TargetType
from mandos.model.hits import Triple
from mandos.model.pubchem_api import (
    CachingPubchemApi,
    QueryingPubchemApi,
    PubchemCompoundLookupError,
)
from mandos.model.searches import Search
from mandos.model.taxonomy import Taxonomy
from mandos.model.taxonomy_caches import TaxonomyFactories
from mandos.model.settings import MANDOS_SETTINGS
from mandos.search.chembl.binding_search import BindingSearch
from mandos.search.chembl.atc_search import AtcSearch
from mandos.search.chembl.go_search import GoType, GoSearch
from mandos.search.chembl.indication_search import IndicationSearch
from mandos.search.chembl.mechanism_search import MechanismSearch

logger = logging.getLogger(__package__)
cli = typer.Typer()


class Searcher:
    def __init__(self, search: Search):
        self.what = search

    def search(
        self,
        path: Path,
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """
        Process data.

        Args:
            path: Path to the input file of one of the formats:
                - .txt containing one key (InChI / CHEMBL ID) per line
                - .csv/.tsv/.tab containing one key per row
                - .csv/.tsv/.tab of a symmetric affinity matrix, with a row header and column header with the keys

        Returns:

        """
        df, triples = self.search_for(path)
        df_out = Path(str(path.with_suffix("")) + "-" + self.what.search_name.lower() + ".csv")
        df.to_csv(df_out)
        triples_out = df_out.with_suffix(".triples.txt")
        triples_out.write_text("\n".join([t.statement for t in triples]), encoding="utf8")
        triples_out.write_text(
            "\n".join([Triple.tab_header(), *[t.tabs for t in triples]]), encoding="utf8"
        )
        return df, triples

    def search_for(
        self,
        compounds: Union[Sequence[str], PurePath],
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """

        Args:
            compounds:

        Returns:

        """
        if isinstance(compounds, (PurePath, str)):
            compounds = Path(compounds).read_text(encoding="utf8").splitlines()
        compounds = [c.strip() for c in compounds if len(c.strip()) > 0]
        cache = CachingPubchemApi(MANDOS_SETTINGS.pubchem_cache_path, QueryingPubchemApi())
        compounds = list(compounds)
        # TODO
        for compound in compounds:
            try:
                cache.fetch_data(compound)
            except PubchemCompoundLookupError:
                logger.error(f"Did not find compound {compound}")
                logger.debug(f"Did not find compound {compound}", exc_info=True)
        hits = self.what.find_all(compounds)
        # collapse over and sort the triples
        triples = sorted(list({hit.to_triple() for hit in hits}))
        df = pd.DataFrame(
            [pd.Series({f: getattr(h, f) for f in self.what.hit_fields()}) for h in hits]
        )
        return df, triples


class Utils:
    @staticmethod
    def split(st: str) -> Set[str]:
        return {s.strip() for s in st.split(",")}

    @staticmethod
    def get_taxon(taxon: int) -> Taxonomy:
        return TaxonomyFactories.from_uniprot(MANDOS_SETTINGS.taxonomy_cache_path).load(taxon)

    @staticmethod
    def get_target_types(st: str) -> Set[str]:
        st = st.strip()
        if st == "all":
            return {str(s) for s in TargetType.all_types()}
        if st == "known":
            return {str(s) for s in TargetType.all_types() if not s.is_unknown}
        if st == "protein":
            return {str(s) for s in TargetType.protein_types()}
        return Utils.split(st)


class Commands:
    """
    Entry points for mandos.
    """

    @staticmethod
    @cli.command("chembl:binding")
    def binding(
        path: Path,
        taxon: int = 7742,
        traversal_strategy: str = "strategy0",
        target_types: str = "single_protein,protein_family,protein_complex,protein_complex_group,selectivity_group",
        min_confidence: int = 3,
        relations: str = "<,<=,=",
        min_pchembl: float = 6.0,
        banned_flags: str = "potential missing data,potential transcription error,outside typical range",
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """
        Process data.
        """
        api = ChemblApi.wrap(Chembl)
        search = BindingSearch(
            chembl_api=api,
            tax=Utils.get_taxon(taxon),
            traversal_strategy=traversal_strategy,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=min_confidence,
            allowed_relations=Utils.split(relations),
            min_pchembl=min_pchembl,
            banned_flags=Utils.split(banned_flags),
        )
        return Searcher(search).search(path)

    @staticmethod
    @cli.command("chembl:mechanism")
    def moa(
        path: Path,
        taxon: int = 7742,
        traversal_strategy: str = "strategy0",
        target_types: str = "single_protein,protein_family,protein_complex,protein_complex_group,selectivity_group",
        min_confidence: int = 3,
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """
        Process data.
        """
        api = ChemblApi.wrap(Chembl)
        search = MechanismSearch(
            chembl_api=api,
            tax=Utils.get_taxon(taxon),
            traversal_strategy=traversal_strategy,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=min_confidence,
        )
        return Searcher(search).search(path)

    @staticmethod
    @cli.command("chembl:trials")
    def trials(
        path: Path,
        min_phase: int = 3,
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """
        Process data.
        """
        api = ChemblApi.wrap(Chembl)
        search = IndicationSearch(
            chembl_api=api,
            min_phase=min_phase,
        )
        return Searcher(search).search(path)

    @staticmethod
    @cli.command("chembl:atc")
    def atc(
        path: Path,
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """
        Process data.
        """
        api = ChemblApi.wrap(Chembl)
        search = AtcSearch(
            chembl_api=api,
        )
        return Searcher(search).search(path)

    @staticmethod
    @cli.command("chembl:go")
    def go_search(
        path: Path,
        kind: GoType,
        taxon: int = 7742,
        traversal_strategy: str = "strategy0",
        target_types: str = "single_protein,protein_family,protein_complex,protein_complex_group,selectivity_group",
        min_confidence: int = 3,
        relations: str = "<,<=,=",
        min_pchembl: float = 6.0,
        banned_flags: str = "potential missing data,potential transcription error,outside typical range",
    ) -> Tup[pd.DataFrame, Sequence[Triple]]:
        """
        Process data.
        """
        api = ChemblApi.wrap(Chembl)
        api = ChemblApi.wrap(Chembl)
        binding_search = BindingSearch(
            chembl_api=api,
            tax=Utils.get_taxon(taxon),
            traversal_strategy=traversal_strategy,
            allowed_target_types=Utils.get_target_types(target_types),
            min_confidence_score=min_confidence,
            allowed_relations=Utils.split(relations),
            min_pchembl=min_pchembl,
            banned_flags=Utils.split(banned_flags),
        )
        search = GoSearch(api, kind, binding_search)
        return Searcher(search).search(path)

    @staticmethod
    @cli.command(hidden=True)
    def process_tax(
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


if __name__ == "__main__":
    cli()


__all__ = ["Commands", "Searcher"]
