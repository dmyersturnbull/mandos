import pytest
from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.api import ChemblApi, ChemblEntrypoint, ChemblFilterQuery
from mandos.model.targets import Target, TargetFactory, TargetType


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
        assert target.id == 4444
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
            dict(relationship="SUPERSET OF", related_target_chembl_id="CHEMBL1111"),
            dict(relationship="SUPERSET OF", related_target_chembl_id="CHEMBL0000"),
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
        assert len(target.parents()) == 2
        # should sort by CHEMBL ID first, so 0000 will be first
        parent: Target = target.parents()[0]
        assert parent.name == "receptor"
        assert parent.chembl == "CHEMBL0000"
        parent: Target = target.parents()[1]
        assert parent.name == "monoamine transporter"
        assert parent.chembl == "CHEMBL1111"


if __name__ == "__main__":
    pytest.main()
