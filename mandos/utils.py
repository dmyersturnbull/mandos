import logging
from dataclasses import dataclass

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True)
class ChemblCompound:
    chid: str
    inchikey: str
    name: str


class Utils:
    @classmethod
    def get_target(cls, chembl: str) -> NestedDotDict:
        targets = Chembl.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
        return NestedDotDict(targets[0])

    @classmethod
    def get_compound(cls, inchikey: str) -> ChemblCompound:
        ch = NestedDotDict(Chembl.molecule.get(inchikey))
        chid = ch["molecule_chembl_id"]
        inchikey = ch["molecule_structures"]["standard_inchi_key"]
        name = ch["pref_name"]
        return ChemblCompound(chid, inchikey, name)
