import decorateme

from mandos.model.apis.caching_pubchem_api import CachingPubchemApi
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.chembl_scrape_api import (
    CachingChemblScrapeApi,
    ChemblScrapeApi,
    QueryingChemblScrapeApi,
)
from mandos.model.apis.g2p_api import CachingG2pApi, G2pApi
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi
from mandos.model.settings import SETTINGS


@decorateme.auto_repr_str()
class Apis:

    Pubchem: PubchemApi = None
    Chembl: ChemblApi = None
    ChemblScrape: ChemblScrapeApi = None
    G2p: G2pApi = None

    @classmethod
    def set(
        cls, chembl: ChemblApi, pubchem: PubchemApi, g2p: G2pApi, chembl_scrape: ChemblScrapeApi
    ) -> None:
        cls.Chembl = chembl
        cls.Pubchem = pubchem
        cls.G2p = g2p
        cls.ChemblScrape = chembl_scrape
        SETTINGS.configure()

    @classmethod
    def set_default(cls, pubchem: bool = True, chembl: bool = True, g2p: bool = True) -> None:
        if chembl:
            from chembl_webresource_client.new_client import new_client as _Chembl

            cls.Chembl = ChemblApi.wrap(_Chembl)
            cls.ChemblScrape = CachingChemblScrapeApi(QueryingChemblScrapeApi())
        if pubchem:
            cls.Pubchem = CachingPubchemApi(QueryingPubchemApi())
        if g2p:
            cls.G2p = CachingG2pApi()
        SETTINGS.configure()


__all__ = ["Apis"]
