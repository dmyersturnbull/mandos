from datetime import date
from pathlib import Path

import pytest

from mandos.pubchem_api import CachingPubchemApi
from mandos.model.pubchem_support.pubchem_models import (
    Codes,
    CoOccurrenceType,
    AtcCode,
    CompoundGeneInteraction,
    DrugbankDdi,
    DrugGeneInteraction,
    CoOccurrence,
    Activity,
    AssayType,
    Bioactivity,
)


class TestPubchemData:
    def test(self):
        pass  # nav = PubchemData()


class TestPubchemApi:
    def test(self):
        path = Path(__file__).parent / "resources" / "pchem_store"
        querier = CachingPubchemApi(path, None, compress=False)
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
        assert drug.livertox_classes == {"Central Nervous System Stimulants"}
        assert drug.indication_summary_livertox == "Cocaine is a benzoid acid ester."
        # assert drug.clinical_trials == set()
        pharm = x.pharmacology_and_biochemistry
        assert (
            pharm.summary_drugbank_text
            == "From DrugBank Pharmacology: Cocaine is a local anesthetic."
        )
        assert pharm.summary_ncit_text == "From NCIt: Cocaine is a tropane alkaloid."
        assert pharm.summary_ncit_links == frozenset({"cocaineish", "somencitthing"})
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
        assert pharm.moa_summary_drugbank_links == frozenset({"drugbankmoacocaine"})
        assert pharm.moa_summary_drugbank_text == "From DrugBank MOA: Cocaine anesthesia."
        assert pharm.moa_summary_hsdb_links == frozenset(
            {"fromhsdb:jwh133", "fromhsdb: hydrochloride"}
        )
        assert (
            pharm.moa_summary_hsdb_text
            == "From HSDB / lit: Cocaine is something. /// And something else."
        )
        assert pharm.biochem_reactions == frozenset({"Metabolism", "Biological oxidations"})
        safety = x.safety_and_hazards
        assert {g.code for g in safety.ghs_codes} == {"H311", "H301"}
        tox = x.toxicity
        assert tox.acute_effects == frozenset(
            {
                "an effect",
                "behavioral: convulsions or effect on seizure threshold",
                "behavioral: excitement",
            }
        )
        lit = x.literature
        chem_co = lit.chemical_cooccurrences
        assert frozenset([c.strip_pubs() for c in chem_co]) == frozenset(
            {
                CoOccurrence(
                    neighbor_id="681",
                    neighbor_name="Dopamine",
                    kind=CoOccurrenceType.chemical,
                    article_count=4991,
                    query_article_count=37869,
                    neighbor_article_count=104868,
                    score=144197,
                    publications=frozenset(),
                )
            }
        )
        # TODO: test pubs
        gene_co = lit.gene_cooccurrences
        assert frozenset([c.strip_pubs() for c in gene_co]) == frozenset(
            {
                CoOccurrence(
                    neighbor_id="slc6a3",
                    neighbor_name="solute carrier family 6 member 3",
                    kind=CoOccurrenceType.gene,
                    article_count=1142,
                    query_article_count=9031,
                    neighbor_article_count=6295,
                    score=49087,
                    publications=frozenset(),
                )
            }
        )
        disease_co = lit.disease_cooccurrences
        assert frozenset([c.strip_pubs() for c in disease_co]) == frozenset(
            {
                CoOccurrence(
                    neighbor_id="D010146",
                    neighbor_name="Pain",
                    kind=CoOccurrenceType.disease,
                    article_count=524,
                    query_article_count=24423,
                    neighbor_article_count=159582,
                    score=12499,
                    publications=frozenset(),
                ),
                CoOccurrence(
                    neighbor_id="D019966",
                    neighbor_name="Substance-Related Disorders",
                    kind=CoOccurrenceType.disease,
                    article_count=8944,
                    query_article_count=24423,
                    neighbor_article_count=43314,
                    score=287471,
                    publications=frozenset(),
                ),
            }
        )
        bio = x.biomolecular_interactions_and_pathways
        assert bio.drug_gene_interactions == frozenset(
            {
                DrugGeneInteraction(
                    gene_name="OPRK1",
                    gene_claim_id="P41145",
                    source="TdgClinicalTrial",
                    interactions=frozenset(),
                    pmids=frozenset(),
                    dois=frozenset(),
                ),
                DrugGeneInteraction(
                    gene_name="DRD3",
                    gene_claim_id="P35462",
                    source="TEND",
                    interactions=frozenset(),
                    pmids=frozenset(),
                    dois=frozenset(),
                ),
                DrugGeneInteraction(
                    gene_name="SCN1A",
                    gene_claim_id="BE0004901",
                    source="DrugBank",
                    interactions=frozenset({"inhibitor"}),
                    pmids=frozenset({Codes.PubmedId("9876137"), Codes.PubmedId("2155033")}),
                    dois=frozenset(
                        {
                            Codes.Doi("10.1016/s0006-3495(90)82574-1"),
                            Codes.Doi("10.1016/s0006-3495(99)77192-4"),
                        }
                    ),
                ),
                DrugGeneInteraction(
                    gene_name="CNR1",
                    gene_claim_id="CNR1",
                    source="PharmGKB",
                    interactions=frozenset(),
                    pmids=frozenset(),
                    dois=frozenset(),
                ),
            }
        )
        assert bio.compound_gene_interactions == frozenset(
            {
                CompoundGeneInteraction(
                    gene_name=Codes.GeneId("CHRNB2"),
                    interactions=frozenset(
                        {"CHRNB2 protein results in increased susceptibility to Cocaine"}
                    ),
                    tax_name="Mus musculus",
                    pmids=frozenset(),
                ),
                CompoundGeneInteraction(
                    gene_name=Codes.GeneId("CHURC1"),
                    interactions=frozenset(
                        {"Cocaine results in decreased expression of CHURC1 mRNA"}
                    ),
                    tax_name="Homo sapiens",
                    pmids=frozenset({Codes.PubmedId("16710320"), Codes.PubmedId("15009677")}),
                ),
            }
        )
        assert bio.drugbank_legal_groups == frozenset({"approved", "illicit"})
        assert bio.drugbank_ddis == frozenset(
            {
                DrugbankDdi(
                    drug_drugbank_id=Codes.DrugbankCompoundId("DB00007"),
                    drug_pubchem_id=Codes.PubchemCompoundId("657181"),
                    drug_drugbank_name="Leuprolide",
                    description="The risk or severity of QTc prolongation.",
                )
            }
        )
        test = x.biological_test_results
        assert test.bioactivity == frozenset(
            {
                Bioactivity(
                    assay_id=127361,
                    assay_type=AssayType.confirmatory,
                    assay_ref="ChEMBL",
                    assay_name="Binding affinity towards human monoclonal antibody 2E2 using [3H]cocaine",
                    assay_made_date=date(2018, 9, 8),
                    gene_id=None,
                    tax_id=None,
                    pmid=Codes.PubmedId("14695827"),
                    activity=Activity.active,
                    activity_name="Ki",
                    activity_value=0.0035,
                    target_name=None,
                ),
                Bioactivity(
                    assay_id=127359,
                    assay_type=AssayType.confirmatory,
                    assay_ref="ChEMBL",
                    assay_name="Dissociation Constant for human monoclonal antibody 2E2 with [3H]cocaine",
                    assay_made_date=date(2018, 9, 8),
                    gene_id=None,
                    tax_id=None,
                    pmid=Codes.PubmedId("14695827"),
                    activity=Activity.active,
                    activity_name="Kd",
                    activity_value=0.0044,
                    target_name=None,
                ),
            }
        )


if __name__ == "__main__":
    pytest.main()
