from typing import Sequence, Generator

from chembl_webresource_client.new_client import new_client as chembl

#from .model import Compound, Predicate, Target, Activity, Organism


class Api:

    def find(self, compound) -> Generator[str, None, None]:
        compound_id, compound_inchikey, compound_name = self.link(compound)
        data = chembl.activity.filter(molecule_chembl_id=compound_id)
        for m in data:
            target_id = m['target_chembl_id']
            target_name = m.get('target_pref_name', 'CHEMBL'+str(target_id))
            #target = Target(target_id, target_name)
            #yield Activity(compound, 'activity')
            print(m)
            comment = m.get('comment')
            assay_type = m['assay_type'];
            standard_type = m['standard_type'];
            src_id = m['src_id']
            standard_relation = m['standard_relation']
            target_organism = m['target_organism']
            standard_value = float(m['standard_value']) if m['standard_value'] is not None else None

    def link(self, inchikey: str):
        ch = chembl.molecule.get(inchikey)
        chid = ch['molecule_chembl_id']
        inchikey = ch['molecule_structures']['standard_inchi_key']
        name = ch['pref_name']
        return chid, inchikey, name


if __name__ == '__main__':
    Api().find('CHEMBL370805')
