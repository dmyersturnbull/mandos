from datetime import date
from pathlib import Path

import pytest

from mandos.pubchem_api import (
    QueryingPubchemApi,
    CachingPubchemApi,
)
from mandos.model.pubchem_support import (
    Codes,
    CoOccurrenceType,
    AtcCode,
    Publication,
    CoOccurrence,
)


class TestPubchemData:
    def test(self):
        pass  # nav = PubchemData()


class TestPubchemApi:
    def test(self):
        path = Path(__file__).parent / "resources" / "pchem_store"
        querier = CachingPubchemApi(path, QueryingPubchemApi(), compress=False)
        x = querier.fetch_data("PIQVDUKEQYOJNR-VZXSFKIWSA-N")
        assert x.cid == 446220
        assert x.parent_or_self == 446220
        title = x.title_and_summary
        assert title.safety is not None
        assert title.safety == {"Irritant", "Acute Toxic"}
        props = x.chemical_and_physical_properties
        assert props.computed is not None
        assert 0 < len(props.computed) < 40
        drug = x.drug_and_medication_information
        assert drug.indication_summary_drugbank == "Cocaine has indications."
        assert drug.classes == {"Central Nervous System Stimulants"}
        assert drug.indication_summary_livertox == "Cocaine is a benzoid acid ester."
        # assert drug.clinical_trials == set()
        pharm = x.pharmacology_and_biochemistry
        assert pharm.summary_drugbank_text == "Cocaine is a local anesthetic indicated for things."
        assert pharm.summary_ncit_text == "Cocaine is a tropane alkaloid."
        assert pharm.summary_ncit_links == frozenset(
            {"dopamine", "serotonin", "norepinephrine", "cocaine"}
        )
        assert pharm.mesh == frozenset(
            {"Dopamine Uptake Inhibitors", "Anesthetics, Local", "Vasoconstrictor Agents"}
        )
        assert pharm.atc == frozenset(
            {
                AtcCode(code="S02D", name="Other otologicals"),
                AtcCode(code="R02A", name="Throat preparations"),
                AtcCode(code="N01BC01", name="Cocaine"),
                AtcCode(code="R", name="Respiratory system"),
                AtcCode(code="R02AD", name="Anesthetics, local"),
                AtcCode(code="R02", name="Throat preparations"),
                AtcCode(code="R02AD03", name="Cocaine"),
                AtcCode(code="S01", name="Ophthalmologicals"),
                AtcCode(code="S02DA", name="Analgesics and anesthetics"),
                AtcCode(code="N01B", name="Anesthetics, local"),
                AtcCode(code="S01HA", name="Local anesthetics"),
                AtcCode(code="N01BC", name="Esters of benzoic acid"),
                AtcCode(code="S02DA02", name="Cocaine"),
                AtcCode(code="N", name="Nervous system"),
                AtcCode(code="S01HA01", name="Cocaine"),
                AtcCode(code="S", name="Sensory organs"),
                AtcCode(code="S02", name="Otologicals"),
                AtcCode(code="S01H", name="Local anesthetics"),
                AtcCode(code="N01", name="Anesthetics"),
            }
        )
        assert pharm.moa_summary_drugbank_links == frozenset(
            {"norepinephrine", "serotonin", "cocaine", "dopamine"}
        )
        assert (
            pharm.moa_summary_drugbank_text
            == "Cocaine produces anesthesia by inhibiting excitation of nerve endings or by blocking conduction in peripheral nerves. This is achieved by reversibly binding to and inactivating sodium channels. Sodium influx through these channels is necessary for the depolarization of nerve cell membranes and subsequent propagation of impulses along the course of the nerve. Cocaine is the only local anesthetic with vasoconstrictive properties. This is a result of its blockade of norepinephrine reuptake in the autonomic nervous system. Cocaine binds differentially to the dopamine, serotonin, and norepinephrine transport proteins and directly prevents the re-uptake of dopamine, serotonin, and norepinephrine into pre-synaptic neurons. Its effect on dopamine levels is most responsible for the addictive property of cocaine."
        )
        # possible copyright issues with these ones, but they're correct
        assert pharm.moa_summary_hsdb_links
        assert pharm.moa_summary_hsdb_text
        assert pharm.biochem_reactions == frozenset(
            {"Metabolism", "Biological oxidations", "Phase I - Functionalization of compounds"}
        )
        safety = x.safety_and_hazards
        assert {g.code for g in safety.ghs_codes} == {"H331", "H317", "H311", "H301"}
        tox = x.toxicity
        assert tox.acute_effects == frozenset(
            {
                "autonomic nervous system: sympathomimetic",
                "behavioral: altered sleep time (including change in righting " "reflex)",
                "behavioral: convulsions or effect on seizure threshold",
                "behavioral: excitement",
                "behavioral: general anesthetic",
                "cardiac: pulse rate",
                "lungs, thorax, or respiration: respiratory stimulation",
            }
        )
        lit = x.literature
        chem_co = lit.chemical_cooccurrences
        assert frozenset([c.strip_pubs() for c in chem_co]) == frozenset({})
        assert lit.gene_cooccurrences == frozenset({})
        assert lit.disease_cooccurrences == frozenset({})
        assert lit.drug_gene_interactions == frozenset({})
        assert lit.compound_gene_interactions == frozenset({})


if __name__ == "__main__":
    pytest.main()
