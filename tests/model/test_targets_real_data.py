from typing import Mapping

import pytest
from chembl_webresource_client.new_client import new_client as Chembl

from mandos.model.chembl_support.chembl_targets import (
    DagTarget,
    DagTargetLinkType,
    TargetFactory,
    TargetRelationshipType,
    TargetType,
)


class TestTargets:
    def test_traverse_gabaa_up(self):
        target = TargetFactory.find("CHEMBL2109243", Chembl)
        assert target.chembl == "CHEMBL2109243"
        link_types = DagTargetLinkType.cross(
            TargetType.protein_types(),
            {TargetRelationshipType.subset_of},
            TargetType.protein_types(),
        )
        accepted = target.traverse(link_types)
        assert {t.target.chembl for t in accepted} == {"CHEMBL2109243", "CHEMBL2093872"}

    def test_traverse_gabaa_up_mouse(self):
        # a single protein
        # branches to GABA A channel complex group CHEMBL2094133
        # but also to complexes CHEMBL4296058 and CHEMBL4296059
        # weirdly, CHEMBL4296058 then joins up with CHEMBL2094133
        # but CHEMBL4296059 does not (it only joins through an OVERLAPS WITH rel)
        # so that one SHOULD be an "end" (which wouldn't be true in a real traversal strategy, hopefully)
        target = TargetFactory.find("CHEMBL3139", Chembl)
        assert target.chembl == "CHEMBL3139"
        link_types = DagTargetLinkType.cross(
            TargetType.protein_types(),
            {TargetRelationshipType.subset_of},
            TargetType.protein_types(),
        )
        accepted = target.traverse(link_types)
        vals: Mapping[str, DagTarget] = {a.target.chembl: a for a in accepted}
        assert {t.target.chembl for t in accepted} == {
            "CHEMBL2094133",
            "CHEMBL3139",
            "CHEMBL4296058",
            "CHEMBL4296059",
        }
        assert not vals["CHEMBL3139"].is_end
        assert vals["CHEMBL2094133"].is_end
        assert not vals["CHEMBL4296058"].is_end
        assert vals["CHEMBL4296059"].is_end
        assert vals["CHEMBL3139"].depth == 0
        assert vals["CHEMBL2094133"].depth == 1  # breadth-first!
        assert vals["CHEMBL2094133"].depth == 1
        assert vals["CHEMBL4296058"].depth == 1
        assert vals["CHEMBL3139"].link_type is None
        assert vals["CHEMBL2094133"].link_type == DagTargetLinkType(
            TargetType.single_protein,
            TargetRelationshipType.subset_of,
            TargetType.protein_complex_group,
            None,
        )
        assert vals["CHEMBL4296058"].link_type == DagTargetLinkType(
            TargetType.single_protein,
            TargetRelationshipType.subset_of,
            TargetType.protein_complex,
            None,
        )
        assert vals["CHEMBL4296059"].link_type == DagTargetLinkType(
            TargetType.single_protein,
            TargetRelationshipType.subset_of,
            TargetType.protein_complex,
            None,
        )

    def test_traverse_gabaa_up_mouse_2(self):
        # this is about the same, but now we'll allow that OVERLAPS WITH rel
        # so we won't find them here
        target = TargetFactory.find("CHEMBL3139", Chembl)
        assert target.chembl == "CHEMBL3139"
        link_types = DagTargetLinkType.cross(
            TargetType.protein_types(),
            {TargetRelationshipType.subset_of},
            TargetType.protein_types(),
        )
        link_types.add(
            DagTargetLinkType(
                TargetType.protein_complex,
                TargetRelationshipType.overlaps_with,
                TargetType.protein_complex_group,
                None,
            )
        )
        accepted = target.traverse(link_types)
        vals: Mapping[str, DagTarget] = {a.target.chembl: a for a in accepted}
        assert {t.target.chembl for t in accepted} == {
            "CHEMBL2094133",
            "CHEMBL3139",
            "CHEMBL4296058",
            "CHEMBL4296059",
        }
        assert not vals["CHEMBL3139"].is_end
        assert vals["CHEMBL2094133"].is_end
        assert not vals["CHEMBL4296058"].is_end
        # here's the difference:
        # by adding the OVERLAPS WITH rel, it now knows it's not at the end
        assert not vals["CHEMBL4296059"].is_end
        assert vals["CHEMBL3139"].depth == 0
        assert vals["CHEMBL2094133"].depth == 1  # breadth-first!
        assert vals["CHEMBL2094133"].depth == 1
        assert vals["CHEMBL4296058"].depth == 1
        assert vals["CHEMBL3139"].link_type is None
        assert vals["CHEMBL2094133"].link_type == DagTargetLinkType(
            TargetType.single_protein,
            TargetRelationshipType.subset_of,
            TargetType.protein_complex_group,
            None,
        )
        assert vals["CHEMBL4296058"].link_type == DagTargetLinkType(
            TargetType.single_protein,
            TargetRelationshipType.subset_of,
            TargetType.protein_complex,
            None,
        )
        assert vals["CHEMBL4296059"].link_type == DagTargetLinkType(
            TargetType.single_protein,
            TargetRelationshipType.subset_of,
            TargetType.protein_complex,
            None,
        )

    def test_traverse_gabaa_up_and_down(self):
        target = TargetFactory.find("CHEMBL2109243", Chembl)
        link_types = DagTargetLinkType.cross(
            TargetType.protein_types(),
            {TargetRelationshipType.subset_of, TargetRelationshipType.superset_of},
            TargetType.protein_types(),
        )
        accepted = target.traverse(link_types)
        # based on the docs I wrote, originally by looking thru the search results
        assert len(accepted) > 40
        assert len(accepted) < 60
        assert {"GABA" in t.target.name.upper() for t in accepted}


if __name__ == "__main__":
    pytest.main()
