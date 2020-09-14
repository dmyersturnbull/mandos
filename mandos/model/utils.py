import logging
from dataclasses import dataclass

from chembl_webresource_client.new_client import new_client as Chembl
from pocketutils.core.dot_dict import NestedDotDict

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True, repr=True, unsafe_hash=True)
class ChemblCompound:
    chid: str
    inchikey: str
    name: str

    @property
    def chid_int(self) -> int:
        return int(self.chid.replace("CHEMBL", ""))


class Utils:
    @classmethod
    def parse_bool(cls, value: str):
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        else:
            raise ValueError(f"Could not parse {value} to bool")

    @classmethod
    def get_target(cls, chembl: str) -> NestedDotDict:
        targets = Chembl.target.filter(target_chembl_id=chembl)
        assert len(targets) == 1
        return NestedDotDict(targets[0])

    @classmethod
    def get_compound(cls, inchikey: str) -> ChemblCompound:
        ch = cls.get_compound_dot_dict(inchikey)
        chid = ch["molecule_chembl_id"]
        inchikey = ch["molecule_structures"]["standard_inchi_key"]
        name = ch["pref_name"]
        return ChemblCompound(chid, inchikey, name)

    @classmethod
    def get_compound_dot_dict(cls, inchikey: str, use_parent: bool = True) -> NestedDotDict:
        ch = NestedDotDict(Chembl.molecule.get(inchikey))
        parent = ch["molecule_hierarchy"]["parent_chembl_id"]
        if use_parent and parent != ch["molecule_chembl_id"]:
            ch = NestedDotDict(Chembl.molecule.get(parent))
        return ch
