import pytest

from mandos.chembl_api import ChemblApi, ChemblEntrypoint
from mandos.model.targets import Target, TargetFactory, TargetRelationshipType, TargetType


class TestTargets:
    def test_find(self):
        dat = dict(
            target_chembl_id="CHEMBL4444",
            pref_name="dopamine transporter",
            target_type="SINGLE_PROTEIN",
        )
        api = ChemblApi.mock({"target": ChemblEntrypoint.mock({"DAT": dat})})
        target = TargetFactory.find("DAT", api)
        assert isinstance(target, Target)
        assert target.type == TargetType.single_protein
        assert target.name == "dopamine transporter"
        assert target.chembl == "CHEMBL4444"

    def test_parents(self):
        dat = dict(
            target_chembl_id="CHEMBL4444",
            pref_name="dopamine transporter",
            target_type="SINGLE_PROTEIN",
        )
        monoamine = dict(
            target_chembl_id="CHEMBL1111",
            pref_name="monoamine transporter",
            target_type="SINGLE_PROTEIN",
        )
        receptor = dict(
            target_chembl_id="CHEMBL0000", pref_name="receptor", target_type="PROTEIN_COMPLEX"
        )
        relations = [
            dict(relationship="SUBSET OF", related_target_chembl_id="CHEMBL1111"),
            dict(relationship="SUBSET OF", related_target_chembl_id="CHEMBL0000"),
        ]
        get_target = {
            "DAT": dat,
            "CHEMBL4444": dat,
            "CHEMBL1111": monoamine,
            "CHEMBL0000": receptor,
        }

        def filter_targets(kwargs):
            x = kwargs["target_chembl_id"]
            if x == "CHEMBL4444":
                return [dat]
            elif x == "CHEMBL1111":
                return [monoamine]
            elif x == "CHEMBL0000":
                return [receptor]

        def filter_relations(kwargs):
            return relations

        api = ChemblApi.mock(
            {
                "target": ChemblEntrypoint.mock(get_target, filter_targets),
                "target_relation": ChemblEntrypoint.mock({}, filter_relations),
            }
        )
        target = TargetFactory.find("CHEMBL4444", api)
        assert len(target.links({TargetRelationshipType.subset_of})) == 2
        # should sort by CHEMBL ID first, so 0000 will be first
        parent, link_type = target.links({TargetRelationshipType.subset_of})[0]
        assert parent.name == "receptor"
        assert parent.chembl == "CHEMBL0000"
        parent, link_type = target.links({TargetRelationshipType.subset_of})[1]
        assert parent.name == "monoamine transporter"
        assert parent.chembl == "CHEMBL1111"

    def test_traverse_gabaa(self):
        x = dict(
            target_chembl_id="CHEMBL5112",
            pref_name="GABA receptor alpha-5 subunit",
            target_type="SINGLE PROTEIN",
        )
        x_row1 = dict(
            target_chembl_id="CHEMBL2093872",
            pref_name="GABA-A receptor; anion channel",
            target_type="PROTEIN COMPLEX GROUP",
        )
        x_row1_superset = dict(
            target_chembl_id="CHEMBL1111", pref_name="supergroup", target_type="SELECTIVITY FILTER"
        )
        x_row2 = dict(
            target_chembl_id="CHEMBL2094122",
            pref_name="GABA-A receptor; alpha-5/beta-3/gamma-2",
            target_type="PROTEIN COMPLEX",
        )
        x_row3 = dict(
            target_chembl_id="CHEMBL2109243",
            pref_name="GABA-A receptor; benzodiazepine site",
            target_type="PROTEIN COMPLEX GROUP",
        )
        x_row4 = dict(
            target_chembl_id="CHEMBL2109244",
            pref_name="GABA-A receptor; agonist GABA site",
            target_type="PROTEIN COMPLEX GROUP",
        )
        x_row5 = dict(
            target_chembl_id="CHEMBL3885576",
            pref_name="Gamma-aminobutyric acid receptor subunit alpha-5/beta-2",
            target_type="PROTEIN COMPLEX",
        )
        x_row6 = dict(
            target_chembl_id="CHEMBL3885577",
            pref_name="Gamma-aminobutyric acid receptor subunit alpha-5/beta-3/gamma-3",
            target_type="PROTEIN COMPLEX",
        )
        x_row7 = dict(
            target_chembl_id="CHEMBL4296057",
            pref_name="Gamma-aminobutyric acid receptor subunit alpha-5/beta-3",
            target_type="PROTEIN COMPLEX",
        )
        xrow2_row2 = x_row1
        xrow3_row3 = x_row1
        xrow4_row5 = x_row1
        xrow5_row3 = x_row1
        xrow5_row7 = x_row4
        relations = [
            dict(relationship="SUBSET OF", related_target_chembl_id="CHEMBL1111"),
            dict(relationship="SUBSET OF", related_target_chembl_id="CHEMBL0000"),
        ]
        # TODO


if __name__ == "__main__":
    pytest.main()
