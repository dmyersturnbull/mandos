from datetime import date
from pathlib import Path

import pytest

from mandos.pubchem_api import (
    QueryingPubchemApi,
    CachingPubchemApi,
)
from mandos.model.pubchem_support import (
    CodeTypes,
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
        querier = CachingPubchemApi(Path("."), QueryingPubchemApi(), compress=False)
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
        assert (
            drug.indication_summary_drugbank
            == "For the introduction of local (topical) anesthesia of accessible mucous membranes of the oral, laryngeal and nasal cavities."
        )
        assert drug.classes == {"Central Nervous System Stimulants"}
        assert (
            drug.indication_summary_livertox
            == "Cocaine is a benzoid acid ester that that was originally used as a local anesthetic, but is no longer used because of its potent addictive qualities. When given in high doses systemically, cocaine has mood elevating effects that have led to its widescale abuse. High doses of cocaine can be associated with toxic reactions including hyperthermia, rhabdomyolysis, shock and acute liver injury which can be severe and even fatal."
        )
        # assert drug.clinical_trials == set()
        pharm = x.pharmacology_and_biochemistry
        assert (
            pharm.summary_drugbank_text
            == "Cocaine is a local anesthetic indicated for the introduction of local (topical) anesthesia of accessible mucous membranes of the oral, laryngeal and nasal cavities."
        )
        assert (
            pharm.summary_ncit_text
            == "Cocaine is a tropane alkaloid with central nervous systems (CNS) stimulating and local anesthetic activity. Cocaine binds to the dopamine, serotonin, and norepinephrine transport proteins and inhibits the re-uptake of dopamine, serotonin, and norepinephrine into pre-synaptic neurons. This leads to an accumulation of the respective neurotransmitters in the synaptic cleft and may result in increased postsynaptic receptor activation. The mechanism of action through which cocaine exerts its local anesthetic effects is by binding to and blocking the voltage-gated sodium channels in the neuronal cell membrane. By stabilizing neuronal membranes, cocaine inhibits the initiation and conduction of nerve impulses and produces a reversible loss of sensation."
        )
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
        assert lit.chemical_cooccurrences
        assert lit.gene_cooccurrences
        assert lit.disease_cooccurrences
        dgis = lit.drug_gene_interactions
        assert dgis
        cgis = lit.compound_gene_interactions
        assert cgis == frozenset({})


if __name__ == "__main__":
    pytest.main()
