from mandos.model.chembl_api import ChemblApi
from mandos.model.pubchem_api import PubchemApi
from mandos.model.querying_pubchem_api import QueryingPubchemApi
from mandos.model.caching_pubchem_api import CachingPubchemApi
from mandos.model.settings import MANDOS_SETTINGS


class Apis:

    Pubchem = None
    Chembl = None

    @classmethod
    def set(cls, chembl: ChemblApi, pubchem: PubchemApi) -> None:
        cls.Chembl = chembl
        cls.Pubchem = pubchem

    @classmethod
    def set_default(cls) -> None:
        from chembl_webresource_client.new_client import new_client as _Chembl

        cls.Pubchem = CachingPubchemApi(MANDOS_SETTINGS.pubchem_cache_path, QueryingPubchemApi())
        cls.Chembl = ChemblApi.wrap(_Chembl)
        MANDOS_SETTINGS.set()


__all__ = ["Apis"]
