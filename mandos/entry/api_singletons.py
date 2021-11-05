import decorateme

from mandos.model.apis.caching_pubchem_api import CachingPubchemApi
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_scrape_api import (
    CachingChemblScrapeApi,
    ChemblScrapeApi,
    QueryingChemblScrapeApi,
)
from mandos.model.apis.g2p_api import CachingG2pApi, G2pApi
from mandos.model.apis.hmdb_api import CachingHmdbApi, HmdbApi, QueryingHmdbApi
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.pubchem_similarity_api import (
    CachingPubchemSimilarityApi,
    QueryingPubchemSimilarityApi,
)
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi
from mandos.model.apis.similarity_api import SimilarityApi
from mandos.model.settings import SETTINGS
from mandos.model.utils.setup import logger


@decorateme.auto_utils()
class Apis:

    Pubchem: PubchemApi = None
    Chembl: ChemblApi = None
    ChemblScrape: ChemblScrapeApi = None
    G2p: G2pApi = None
    Hmdb: HmdbApi = None
    Similarity: SimilarityApi = None

    @classmethod
    def set(
        cls,
        *,
        chembl: ChemblApi,
        pubchem: PubchemApi,
        g2p: G2pApi,
        hmdb: HmdbApi,
        chembl_scrape: ChemblScrapeApi,
        similarity: SimilarityApi,
    ) -> None:
        cls.Chembl = chembl
        cls.Pubchem = pubchem
        cls.G2p = g2p
        cls.Hmdb = hmdb
        cls.ChemblScrape = chembl_scrape
        cls.Similarity = similarity
        logger.debug("Set custom API singletons")

    @classmethod
    def set_default(
        cls,
        *,
        pubchem: bool = True,
        chembl: bool = True,
        hmdb: bool = True,
        g2p: bool = True,
        scrape: bool = True,
        similarity: bool = True,
    ) -> None:
        if chembl:
            from chembl_webresource_client.new_client import new_client as _Chembl

            cls.Chembl = ChemblApi.wrap(_Chembl)
        if pubchem:
            cls.Pubchem = CachingPubchemApi(QueryingPubchemApi())
        if hmdb:
            cls.Hmdb = CachingHmdbApi(QueryingHmdbApi())
        if g2p:
            cls.G2p = CachingG2pApi()
        if scrape:
            cls.ChemblScrape = CachingChemblScrapeApi(QueryingChemblScrapeApi())
        if similarity:
            cls.Similarity = CachingPubchemSimilarityApi(QueryingPubchemSimilarityApi())
        logger.debug("Set default singletons")


__all__ = ["Apis"]
