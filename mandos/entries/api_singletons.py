from mandos.model.apis.caching_pubchem_api import CachingPubchemApi
from mandos.model.apis.chembl_api import ChemblApi
from mandos.model.apis.g2p_api import CachedG2pApi, G2pApi
from mandos.model.apis.pubchem_api import PubchemApi
from mandos.model.apis.querying_pubchem_api import QueryingPubchemApi
from mandos.model.settings import MANDOS_SETTINGS


class Apis:

    Pubchem = None
    Chembl = None
    G2p = None

    @classmethod
    def set(cls, chembl: ChemblApi, pubchem: PubchemApi, g2p: G2pApi) -> None:
        cls.Chembl = chembl
        cls.Pubchem = pubchem
        cls.G2p = g2p

    @classmethod
    def set_default(cls, pubchem: bool = True, chembl: bool = True, g2p: bool = True) -> None:
        if chembl:
            from chembl_webresource_client.new_client import \
                new_client as _Chembl

            cls.Chembl = ChemblApi.wrap(_Chembl)
        if pubchem:
            cls.Pubchem = CachingPubchemApi(
                MANDOS_SETTINGS.pubchem_cache_path, QueryingPubchemApi()
            )
        if g2p:
            cls.G2p = CachedG2pApi(MANDOS_SETTINGS.g2p_cache_path)
        MANDOS_SETTINGS.configure()


__all__ = ["Apis"]
