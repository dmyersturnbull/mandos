"""
PubChem data views and processors.
"""
from __future__ import annotations

import abc
import re
from datetime import date, datetime
from typing import Mapping, Optional, Sequence, Union, FrozenSet, Any, Dict
from typing import Tuple as Tup
from urllib.parse import unquote as url_unescape

import orjson
from pocketutils.core.exceptions import MultipleMatchesError
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.tools.common_tools import CommonTools
from pocketutils.tools.string_tools import StringTools

from mandos import logger

# noinspection PyProtectedMember
from mandos.model.pubchem_support._nav_fns import Filter, Mapx, Flatmap

# noinspection PyProtectedMember
from mandos.model.pubchem_support._nav_model import FilterFn

# noinspection PyProtectedMember
from mandos.model.pubchem_support._nav import JsonNavigator
from mandos.model.pubchem_support.pubchem_models import (
    ComputedProperty,
    Codes,
    CoOccurrenceType,
    ClinicalTrial,
    GhsCode,
    AssociatedDisorder,
    AtcCode,
    DrugbankInteraction,
    DrugbankDdi,
    PubmedEntry,
    Publication,
    AssayType,
    Activity,
    CoOccurrence,
    DrugGeneInteraction,
    ChemicalGeneInteraction,
    Bioactivity,
    AcuteEffectEntry,
    DrugbankTargetType,
)


class Misc:
    empty_frozenset = frozenset([])


class Patterns:
    ghs_code = re.compile(r"((?:H\d+)(?:\+H\d+)*)")
    ghs_code_singles = re.compile(r"(H\d+)")
    pubchem_compound_url = re.compile(r"^https:\/\/pubchem\.ncbi\.nlm\.nih\.gov\/compound\/(.+)$")
    atc_codes = re.compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?")
    mesh_codes = re.compile(r"[A-Z]")


class PubchemDataView(metaclass=abc.ABCMeta):
    """"""

    def __init__(self, data: NestedDotDict):
        self._data = data

    def to_json(self) -> str:
        def default(obj: Any) -> Any:
            if isinstance(obj, NestedDotDict):
                # noinspection PyProtectedMember
                return dict(obj._x)

        # noinspection PyProtectedMember
        data = dict(self._data._x)
        encoded = orjson.dumps(data, default=default, option=orjson.OPT_INDENT_2)
        encoded = encoded.decode(encoding="utf8")
        encoded = StringTools.retab(encoded, 2)
        return encoded

    @property
    def cid(self) -> int:
        if self._data["record.RecordType"] != "CID":
            raise ValueError(
                "RecordType for {} is {}".format(
                    self._data["record.RecordNumber"], self._data["record.RecordType"]
                )
            )
        return self._data["record.RecordNumber"]

    @property
    def _toc(self) -> JsonNavigator:
        return self._nav / "Section" % "TOCHeading"

    @property
    def _tables(self) -> JsonNavigator:
        return JsonNavigator.create(self._data) / "external_tables"

    @property
    def _links(self) -> JsonNavigator:
        return JsonNavigator.create(self._data) / "link_sets"

    @property
    def _classifications(self) -> JsonNavigator:
        return self._nav / "classifications"

    @property
    def _nav(self) -> JsonNavigator:
        return JsonNavigator.create(self._data) / "record"

    @property
    def _refs(self) -> Mapping[int, str]:
        return {z["ReferenceNumber"]: z["SourceName"] for z in (self._nav / "Reference").contents}

    def _has_ref(self, name: str) -> FilterFn:
        return FilterFn(lambda dot: self._refs.get(dot.get_as("ReferenceNumber", int)) == name)


class PubchemMiniDataView(PubchemDataView, metaclass=abc.ABCMeta):
    """"""

    @property
    def _whoami(self) -> str:
        raise NotImplementedError()

    @property
    def _mini(self) -> JsonNavigator:
        return self._toc / self._whoami / "Section" % "TOCHeading"


class TitleAndSummary(PubchemDataView):
    """"""

    @property
    def safety(self) -> FrozenSet[str]:
        return (
            self._toc
            / "Chemical Safety"
            / "Information"
            / self._has_ref("PubChem")
            / "Value"
            / "StringWithMarkup"
            / "Markup"
            >> "Extra"
        ).to_set


class RelatedRecords(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Related Records"

    @property
    def parent(self) -> Optional[int]:
        parent = (
            self._mini
            / "Parent Compound"
            / "Information"
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Flatmap.require_only()
        )
        parent = parent / Mapx.extract_group_1(r"CID (\d+) +.*") // Flatmap.request_only()
        return self.cid if parent.get is None else int(parent.get)


class NamesAndIdentifiers(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Names and Identifiers"

    @property
    def inchikey(self) -> str:
        return self.descriptor("InChI Key")

    @property
    def inchi(self) -> str:
        return self.descriptor("InChI")

    @property
    def molecular_formula(self) -> str:
        return (
            self._mini
            / "Molecular Formula"
            / "Information"
            / self._has_ref("PubChem")
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Flatmap.require_only()
            // Flatmap.require_only()
        ).get

    def descriptor(self, key: str) -> str:
        return (
            self._mini
            / "Computed Descriptors"
            / "Section"
            % "TOCHeading"
            / key
            / "Information"
            / self._has_ref("PubChem")
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Flatmap.require_only()
            // Flatmap.require_only()
        ).get

    @property
    def create_date(self) -> date:
        return (
            self._toc
            / "Create Date"
            / "Information"
            / self._has_ref("PubChem")
            / "Value"
            // ["DateISO8601"]
            // Flatmap.require_only()
            / date.fromisoformat
            // Flatmap.require_only()
        ).get

    @property
    def modify_date(self) -> date:
        return (
            self._toc
            / "Modify Date"
            / "Information"
            / self._has_ref("PubChem")
            / "Value"
            // ["DateISO8601"]
            // Flatmap.require_only()
            / date.fromisoformat
            // Flatmap.require_only()
        ).get


class ChemicalAndPhysicalProperties(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Chemical and Physical Properties"

    @property
    def xlogp3(self) -> str:
        return self.single_property("XLogP3").req_is(float)

    @property
    def mol_weight(self) -> str:
        weight = self.single_property("Molecular Weight")
        if weight.unit != "g/mol":
            raise ValueError(f"Expected g/mol for weight; got {weight.unit}")
        return weight.req_is(float)

    @property
    def tpsa(self) -> str:
        weight = self.single_property("Topological Polar Surface Area")
        if weight.unit != "Å²":
            raise ValueError(f"Expected Å² for weight; got {weight.unit}")
        return weight.req_is(float)

    @property
    def charge(self) -> int:
        return self.single_property("Formal Charge", "PubChem").value

    @property
    def complexity_rating(self) -> int:
        return self.single_property("Complexity", "PubChem").value

    def single_property(self, key: str, ref: Optional[str] = "PubChem") -> ComputedProperty:
        return CommonTools.only(
            [kvr for kvr in self.computed if kvr.key == key and (ref is None or kvr.ref == ref)]
        )

    @property
    def computed(self) -> FrozenSet[ComputedProperty]:
        cid = self.cid
        props = {
            dot["TOCHeading"]: dot["Information"]
            for dot in (self._mini / "Computed Properties" / "Section").get
        }
        results: Dict[Tup[str, str], ComputedProperty] = {}
        for heading, info in props.items():
            for dot in info:
                try:
                    dot = NestedDotDict(dot)
                    kvr = self._extract_kvr(heading, dot)
                    if kvr is not None:
                        if (kvr.key, kvr.ref) in results:
                            raise MultipleMatchesError(f"Multiple matches for {kvr} on {cid}")
                        results[(kvr.key, kvr.ref)] = kvr
                except (KeyError, ValueError):
                    logger.debug(f"Failed on {dot} for cid {cid}")
                    raise
        return frozenset(results.values())

    def _extract_kvr(self, heading: str, dot: NestedDotDict) -> Optional[ComputedProperty]:
        if "Value" not in dot or "Reference" not in dot:
            return None
        ref = ", ".join(dot["Reference"])
        value, unit = self._extract_value_and_unit(dot["Value"])
        return ComputedProperty(heading, value, unit, ref)

    def _extract_value_and_unit(
        self, dot: NestedDotDict
    ) -> Tup[Union[None, int, str, float, bool], str]:
        value, unit = None, None
        if "Number" in dot and len(["Number"]) == 1:
            value = dot["Number"][0]
        elif "Number" in dot and len(["Number"]) > 1:
            value = ", ".join([str(s) for s in dot["Number"]])
        elif (
            "StringWithMarkup" in dot
            and len(dot["StringWithMarkup"]) == 1
            and "String" in dot["StringWithMarkup"][0]
        ):
            value = dot["StringWithMarkup"][0]["String"]
        elif (
            "StringWithMarkup" in dot
            and len(dot["StringWithMarkup"]) > 1
            and all(["String" in swump for swump in dot["StringWithMarkup"]])
        ):
            value = ", ".join([str(s) for s in dot["StringWithMarkup"]])
        else:
            value = None
        if "Unit" in dot and value is not None:
            unit = dot["Unit"]
        if isinstance(value, str):
            value = value.strip().replace("\n", "").replace("\r", "").strip()
        return value, unit


class DrugAndMedicationInformation(PubchemDataView):
    """"""

    @property
    def mini(self) -> JsonNavigator:
        return self._toc / "Drug and Medication Information" / "Section" % "TOCHeading"

    @property
    def indication_summary_drugbank(self) -> Optional[str]:
        return (
            self.mini
            / "Drug Indication"
            / "Information"
            / self._has_ref("DrugBank")
            / "Value"
            / "StringWithMarkup"
            >> "String"
            >> Flatmap.join_nonnulls()
        ).get

    @property
    def indication_summary_livertox(self) -> Optional[str]:
        return (
            self.mini
            / "LiverTox Summary"
            / "Information"
            / self._has_ref("LiverTox")
            / "Value"
            / "StringWithMarkup"
            >> "String"
            >> Flatmap.join_nonnulls()
        ).get

    @property
    def livertox_classes(self) -> FrozenSet[str]:
        return (
            self.mini
            / "Drug Classes"
            / "Information"
            / self._has_ref("LiverTox")
            / "Value"
            / "StringWithMarkup"
            >> "String"
        ).to_set

    @property
    def dea_class(self) -> FrozenSet[str]:
        return (
            self.mini
            / "DEA Drug Facts"
            / "Information"
            / self._has_ref("Drug Enforcement Administration (DEA)")
            / "Value"
            / "StringWithMarkup"
            >> "String"
        ).to_set

    @property
    def dea_schedule(self) -> Optional[Codes.DeaSchedule]:
        return (
            self.mini
            / "DEA Controlled Substances"
            / "Information"
            / self._has_ref("Drug Enforcement Administration (DEA)")
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Flatmap.require_only()
            / Mapx.extract_group_1(r" *Schedule ([IV]+).*")
            / Codes.DeaSchedule
            // Flatmap.request_only()
        ).get

    @property
    def hsdb_uses(self) -> FrozenSet[str]:
        mesh = "National Library of Medicine's Medical Subject Headings"
        return (
            self.mini
            / "Therapeutic Uses"
            / "Information"
            / self._has_ref("Hazardous Substances Data Bank (HSDB)")
            / FilterFn(lambda dot: dot.req_as("Reference", str).startswith(mesh))
            / "Value"
            / "StringWithMarkup"
            >> "String"
        ).to_set

    @property
    def clinical_trials(self) -> FrozenSet[ClinicalTrial]:
        trials = (self._tables / "clinicaltrials").get
        objs = []
        for trial in trials:
            source = self._refs[int(trial["srcid"])]
            obj = ClinicalTrial(
                Codes.ClinicaltrialId.of(trial["ctid"]),
                trial["title"],
                frozenset([Codes.GenericDiseaseCode.of(z) for z in trial["diseaseids"].split("|")]),
                frozenset(trial["conditions"].split("|")),
                trial["phase"],
                trial["status"],
                frozenset(trial["interventions"].split("|")),
                frozenset([Codes.PubchemCompoundId.of(z) for z in trial["cids"].split("|")]),
                source,
            )
            objs.append(obj)
        return frozenset(objs)


class PharmacologyAndBiochemistry(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Pharmacology and Biochemistry"

    @property
    def summary_drugbank_text(self) -> Optional[str]:
        return (
            self._mini
            / "Pharmacology"
            / "Information"
            / self._has_ref("DrugBank")
            / "Value"
            / "StringWithMarkup"
            >> "String"
            >> Flatmap.join_nonnulls()
        ).get

    @property
    def summary_ncit_text(self) -> Optional[str]:
        return (
            self._mini
            / "Pharmacology"
            / "Information"
            / self._has_ref("NCI Thesaurus (NCIt)")
            / Filter.key_equals("Name", "Pharmacology")
            / "Value"
            / "StringWithMarkup"
            >> "String"
            >> Flatmap.join_nonnulls()
        ).get

    @property
    def summary_ncit_links(self) -> FrozenSet[str]:
        return (
            self._mini
            / "Pharmacology"
            / "Information"
            / self._has_ref("NCI Thesaurus (NCIt)")
            / Filter.key_equals("Name", "Pharmacology")
            / "Value"
            / "StringWithMarkup"
            / "Markup"
            / Filter.key_equals("Type", "PubChem Internal Link")
            // ["URL"]
            // Flatmap.require_only()
            / Mapx.extract_group_1(Patterns.pubchem_compound_url)
            / url_unescape
            / Mapx.lowercase_unless_acronym()  # TODO necessary but unfortunate -- cocaine and Cocaine
        ).to_set

    @property
    def mesh(self) -> FrozenSet[str]:
        return (
            self._mini
            / "MeSH Pharmacological Classification"
            / "Information"
            / self._has_ref("MeSH")
            >> "Name"
        ).to_set

    @property
    def atc(self) -> FrozenSet[AtcCode]:
        strs = (
            self._mini
            / "ATC Code"
            / "Information"
            / self._has_ref("WHO Anatomical Therapeutic Chemical (ATC) Classification")
            / Filter.key_equals("Name", "ATC Code")
            / "Value"
            / "StringWithMarkup"
            >> "String"
        ).to_set
        return frozenset(
            [AtcCode(s.split(" - ")[0].strip(), s.split(" - ")[1].strip()) for s in strs]
        )

    @property
    def moa_summary_drugbank_links(self) -> FrozenSet[str]:
        return self._get_moa_links("DrugBank")

    @property
    def moa_summary_drugbank_text(self) -> Optional[str]:
        return self._get_moa_text("DrugBank")

    @property
    def moa_summary_hsdb_links(self) -> FrozenSet[str]:
        return self._get_moa_links("Hazardous Substances Data Bank (HSDB)")

    @property
    def moa_summary_hsdb_text(self) -> Optional[str]:
        return self._get_moa_text("Hazardous Substances Data Bank (HSDB)")

    def _get_moa_text(self, ref: str) -> Optional[str]:
        return (
            self._mini
            / "Mechanism of Action"
            / "Information"
            / self._has_ref(ref)
            / "Value"
            / "StringWithMarkup"
            >> "String"
            >> Flatmap.join_nonnulls(sep=" /// ")
        ).get

    def _get_moa_links(self, ref: str) -> FrozenSet[str]:
        return (
            self._mini
            / "Mechanism of Action"
            / "Information"
            / self._has_ref(ref)
            / "Value"
            / "StringWithMarkup"
            / "Markup"
            / Filter.key_equals("Type", "PubChem Internal Link")
            // ["URL"]
            // Flatmap.require_only()
            / Mapx.extract_group_1(Patterns.pubchem_compound_url)
            / url_unescape
            / Mapx.lowercase_unless_acronym()  # TODO necessary but unfortunate -- cocaine and Cocaine
        ).to_set

    @property
    def biochem_reactions(self) -> FrozenSet[str]:
        # TODO from multiple sources
        return frozenset({s.strip() for s in (self._tables / "pathwayreaction" >> "name").to_set})


class SafetyAndHazards(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Safety and Hazards"

    @property
    def ghs_codes(self) -> FrozenSet[GhsCode]:
        codes = (
            self._mini
            / "Hazards Identification"
            / "Section"
            % "TOCHeading"
            / "GHS Classification"
            / "Information"
            / self._has_ref("European Chemicals Agency (ECHA)")
            / Filter.key_equals("Name", "GHS Hazard Statements")
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Flatmap.require_only()
            / Mapx.extract_group_1(r"^(H\d+)[ :].*$")
            // Mapx.split_and_flatten_nonnulls("+")  # TODO: how is this being used to flatten?
        ).get
        return frozenset([GhsCode.find(code) for code in codes])


class Toxicity(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Toxicity"

    @property
    def acute_effects(self) -> FrozenSet[AcuteEffectEntry]:
        return (
            self._tables
            / "chemidplus"
            // ["gid", "effect", "organism", "testtype", "route", "dose"]
            / FilterFn(lambda dot: dot.get_as("effect", str) is not None)
            / [
                int,
                Mapx.split_to(Codes.ChemIdPlusEffect.of, ";"),
                Codes.ChemIdPlusOrganism.of,
                str,
                str,
                str,
            ]
            // Flatmap.construct(AcuteEffectEntry)
        ).to_set


class AssociatedDisordersAndDiseases(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Associated Disorders and Diseases"

    @property
    def associated_disorders_and_diseases(self) -> FrozenSet[AssociatedDisorder]:
        return (
            self._tables
            / "ctd_chemical_disease"
            // ["gid", "diseaseextid", "diseasename", "directevidence", "dois"]
            / [str, Codes.MeshCode.of, Mapx.req_is(str), Mapx.req_is(str), Mapx.n_bar_items()]
            // Flatmap.construct(AssociatedDisorder)
        ).to_set


class Literature(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Literature"

    @property
    def depositor_pubmed_articles(self) -> FrozenSet[PubmedEntry]:
        def split_mesh_headings(s: str) -> FrozenSet[Codes.MeshHeading]:
            # this is a nightmare
            # these fields are comma-delimited strings, but there are commas within each
            # all of the examples I've seen with this are for chem name cis/trans
            # we can fix those
            # however, there may be some left incorrectly split
            # and it's possible that we join some when we shouldn't
            # ex: 6-Cyano-7-nitroquinoxaline-2,3-dione,Animals,Anticonvulsants,Cocaine,Death, [...]
            # ex: 2,3,4,5-Tetrahydro-7,8-dihydroxy-1-phenyl-1H-3-benzazepine,Animals,Benzazepines, [...]
            if s is None:
                return Misc.empty_frozenset
            bits = []
            current_bit = " "
            for bit in s.split(","):
                if current_bit[-1].isdigit() and bit[0].isdigit():
                    current_bit += bit
                else:
                    bits.append(current_bit.strip())
                    current_bit = bit
            # get the one at the end
            bits.append(current_bit)
            return frozenset({b.strip() for b in bits if b.strip() != ""})

        def split_mesh_subheadings(s: Optional[str]) -> FrozenSet[Codes.MeshSubheading]:
            if s is None:
                return Misc.empty_frozenset
            return frozenset({k.strip() for k in s.split(",") if k.strip() != ""})

        def split_mesh_codes(s: Optional[str]) -> FrozenSet[Codes.MeshCode]:
            if s is None:
                return Misc.empty_frozenset
            z = [bit.split(" ")[0] for bit in s.split(",")]
            return frozenset({b.strip() for b in z if b.strip() != ""})

        def split_sources(s: Optional[str]) -> FrozenSet[str]:
            return frozenset(s.split(","))

        def split_cids(s: Optional[str]) -> FrozenSet[int]:
            if s is None:
                return Misc.empty_frozenset
            return frozenset([int(q) for q in s.split(",")])

        def get_text(s: Optional[str]) -> Optional[str]:
            if s is None:
                return None
            return StringTools.strip_brackets_and_quotes(s.strip()).strip()

        keys = {
            "pmid": Codes.PubmedId.of,
            "articletype": Mapx.req_is(str),
            "pmidsrcs": split_sources,
            "meshheadings": split_mesh_headings,
            "meshsubheadings": split_mesh_subheadings,
            "meshcodes": split_mesh_codes,
            "cids": split_cids,
            "articletitle": get_text,
            "articleabstract": get_text,
            "articlejourname": get_text,
            "articlepubdate": Mapx.int_date(),
        }
        entries = (
            self._tables
            / "pubmed"
            // list(keys.keys())
            / list(keys.values())
            // Flatmap.construct(PubmedEntry)
        ).to_set
        return entries

    @property
    def chemical_cooccurrences(self) -> FrozenSet[CoOccurrence]:
        return self._get_cooccurrences(CoOccurrenceType.chemical)

    @property
    def gene_cooccurrences(self) -> FrozenSet[CoOccurrence]:
        return self._get_cooccurrences(CoOccurrenceType.gene)

    @property
    def disease_cooccurrences(self) -> FrozenSet[CoOccurrence]:
        return self._get_cooccurrences(CoOccurrenceType.disease)

    def _get_cooccurrences(self, kind: CoOccurrenceType) -> FrozenSet[CoOccurrence]:
        links = (self._links / kind.x_name / "LinkDataSet" / "LinkData").get
        results = set()
        for link in links:
            link = NestedDotDict(link)
            try:
                neighbor_id = str(link["ID_2"][kind.id_name])
            except KeyError:
                raise KeyError(f"Could not find ${kind.id_name} in ${link['ID_2']}")
            neighbor_id = self._guess_neighbor(kind, neighbor_id)
            evidence = link["Evidence"][kind.x_name]
            neighbor_name = evidence["NeighborName"]
            ac = evidence["ArticleCount"]
            nac = evidence["NeighborArticleCount"]
            qac = evidence["QueryArticleCount"]
            score = evidence["CooccurrenceScore"]
            articles = [NestedDotDict(k) for k in evidence["Article"]]
            pubs = {
                Publication(
                    pmid=Codes.PubmedId.of(pub["PMID"]),
                    pub_date=datetime.strptime(pub["PublicationDate"].strip(), "%Y-%m-%d").date(),
                    is_review=bool(pub["IsReview"]),
                    title=pub["Title"].strip(),
                    journal=pub["Journal"].strip(),
                    relevance_score=pub.req_as("RelevanceScore", int),
                )
                for pub in articles
            }
            results.add(
                CoOccurrence(
                    neighbor_id=neighbor_id,
                    neighbor_name=neighbor_name,
                    kind=kind,
                    article_count=ac,
                    query_article_count=qac,
                    neighbor_article_count=nac,
                    score=score,
                    publications=frozenset(pubs),
                )
            )
        return frozenset(results)

    def _guess_neighbor(self, kind: CoOccurrenceType, neighbor_id: str) -> str:
        if kind is CoOccurrenceType.chemical:
            return Codes.PubchemCompoundId(neighbor_id)
        elif kind is CoOccurrenceType.gene and neighbor_id.startswith("EC:"):
            return Codes.EcNumber(neighbor_id)
        elif kind is CoOccurrenceType.gene:
            return Codes.GeneId(neighbor_id)
        elif kind is CoOccurrenceType.disease:
            return Codes.MeshCode(neighbor_id)
        else:
            raise ValueError(f"Could not find ID type for {kind} ID {neighbor_id}")


class Patents(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Patents"

    @property
    def associated_disorders_and_diseases(self) -> FrozenSet[AssociatedDisorder]:
        return (
            self._tables
            / "patent"
            // ["diseasename", "directevidence", "dois"]
            / [Mapx.req_is(str), Mapx.req_is(str), Mapx.n_bar_items()]
            // Flatmap.construct(AssociatedDisorder)
        ).to_set


class BiomolecularInteractionsAndPathways(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Biomolecular Interactions and Pathways"

    @property
    def drug_gene_interactions(self) -> FrozenSet[DrugGeneInteraction]:
        # the order of this dict is crucial
        keys = {
            "genename": Mapx.req_is(str, nullable=True),
            "geneclaimname": Mapx.req_is(str, nullable=True),
            "interactionclaimsource": Mapx.req_is(str, nullable=True),
            "interactiontypes": Mapx.split("|", nullable=True),
            "pmids": Mapx.split(",", nullable=True),
            "dois": Mapx.split("|", nullable=True),
        }
        return (
            self._tables
            / "dgidb"
            // list(keys.keys())
            / list(keys.values())
            // Flatmap.construct(DrugGeneInteraction)
        ).to_set

    @property
    def chemical_gene_interactions(self) -> FrozenSet[ChemicalGeneInteraction]:
        # the order of this dict is crucial
        # YES, the | used in pmids really is different from the , used in DrugGeneInteraction
        keys = {
            "genesymbol": Codes.GenecardSymbol.of_nullable,
            "interaction": Mapx.split("|", nullable=True),
            "taxid": Mapx.get_int(nullable=True),
            "taxname": Mapx.req_is(str, True),
            "pmids": Mapx.split("|", nullable=True),
        }
        return (
            self._tables
            / "ctdchemicalgene"
            // list(keys.keys())
            / list(keys.values())
            // Flatmap.construct(ChemicalGeneInteraction)
        ).to_set

    @property
    def drugbank_interactions(self) -> FrozenSet[DrugbankInteraction]:
        keys = {
            "gid": int,
            "genesymbol": Codes.GenecardSymbol,
            "drugaction": Mapx.req_is(str),
            "targetcomponentname": Mapx.req_is(str),
            "targettype": Mapx.req_is(str, then_convert=DrugbankTargetType),
            "targetname": Mapx.req_is(str),
            "generalfunc": Mapx.req_is(str),
            "specificfunc": Mapx.req_is(str),
            "pmids": Mapx.split(","),
            "dois": Mapx.split("|"),
        }
        return (
            self._tables
            / "drugbank"
            // list(keys.keys())
            / list(keys.values())
            // Flatmap.construct(DrugbankInteraction)
        ).to_set

    @property
    def drugbank_legal_groups(self) -> FrozenSet[str]:
        q = set()
        for x in (self._tables / "drugbank" // ["druggroup"] // Flatmap.require_only()).to_set:
            for y in x.split(";"):
                q.add(y.strip())
        return frozenset(q)

    @property
    def drugbank_ddis(self) -> FrozenSet[DrugbankDdi]:
        keys = {
            "dbid2": Codes.DrugbankCompoundId,
            "cid2": Codes.PubchemCompoundId,
            "name": Mapx.req_is(str),
            "descr": Mapx.req_is(str),
        }
        return (
            self._tables
            / "drugbankddi"
            // list(keys.keys())
            / list(keys.values())
            // Flatmap.construct(DrugbankDdi)
        ).to_set


class BiologicalTestResults(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Biological Test Results"

    @property
    def bioactivity(self) -> FrozenSet[Bioactivity]:
        keys = {
            "aid": Mapx.get_int(),
            "aidtype": (lambda s: AssayType[s.lower().strip()]),
            "aidsrcname": Mapx.req_is(str),
            "aidname": Mapx.req_is(str),
            "aidmdate": Mapx.int_date(),
            "geneid": Mapx.str_to(Codes.GeneId, nullable=True, flex_type=True),
            "taxid": Mapx.str_to(str, flex_type=True, nullable=True),
            "pmid": lambda s: None
            if s is None
            else Codes.PubmedId(StringTools.strip_off_end(str(s), ".0")),
            "activity": (lambda s: None if s is None else Activity[s.lower()]),
            "acname": Mapx.str_to(str, nullable=True),
            "acvalue": (lambda x: None if x is None else float(x)),
            "targetname": Mapx.req_is(str, nullable=True),
            "cmpdname": Mapx.req_is(str, nullable=False),
        }
        return (
            self._tables
            / "bioactivity"
            // list(keys.keys())
            / list(keys.values())
            // Flatmap.construct(Bioactivity)
        ).to_set


class Classification(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Classification"

    @property
    def mesh_tree(self) -> Sequence[str]:
        raise NotImplementedError()

    @property
    def chebi_tree(self) -> Sequence[str]:
        raise NotImplementedError()

    @property
    def atc_tree(self) -> FrozenSet[Sequence[str]]:
        raise NotImplementedError()

    @property
    def chemid(self) -> FrozenSet[Sequence[str]]:
        raise NotImplementedError()

    @property
    def g2p_tree(self) -> FrozenSet[Sequence[str]]:
        raise NotImplementedError()

    @property
    def chembl_tree(self) -> FrozenSet[Sequence[str]]:
        raise NotImplementedError()

    @property
    def cpdat_tree(self) -> FrozenSet[Sequence[str]]:
        raise NotImplementedError()

    @property
    def dea(self) -> FrozenSet[str]:
        raise NotImplementedError()


class PubchemData(PubchemDataView):
    @property
    def name(self) -> Optional[str]:
        return self._data.get("record.RecordTitle")

    @property
    def title_and_summary(self) -> TitleAndSummary:
        return TitleAndSummary(self._data)

    @property
    def names_and_identifiers(self) -> NamesAndIdentifiers:
        return NamesAndIdentifiers(self._data)

    @property
    def chemical_and_physical_properties(self) -> ChemicalAndPhysicalProperties:
        return ChemicalAndPhysicalProperties(self._data)

    @property
    def related_records(self) -> RelatedRecords:
        return RelatedRecords(self._data)

    @property
    def drug_and_medication_information(self) -> DrugAndMedicationInformation:
        return DrugAndMedicationInformation(self._data)

    @property
    def pharmacology_and_biochemistry(self) -> PharmacologyAndBiochemistry:
        return PharmacologyAndBiochemistry(self._data)

    @property
    def safety_and_hazards(self) -> SafetyAndHazards:
        return SafetyAndHazards(self._data)

    @property
    def toxicity(self) -> Toxicity:
        return Toxicity(self._data)

    @property
    def literature(self) -> Literature:
        return Literature(self._data)

    @property
    def associated_disorders_and_diseases(self) -> AssociatedDisordersAndDiseases:
        return AssociatedDisordersAndDiseases(self._data)

    @property
    def biomolecular_interactions_and_pathways(self) -> BiomolecularInteractionsAndPathways:
        return BiomolecularInteractionsAndPathways(self._data)

    @property
    def biological_test_results(self) -> BiologicalTestResults:
        return BiologicalTestResults(self._data)

    @property
    def classification(self) -> Classification:
        return Classification(self._data)

    @property
    def parent_or_none(self) -> Optional[int]:
        return self.related_records.parent

    @property
    def parent_or_self(self) -> int:
        parent = self.related_records.parent
        return self.cid if parent is None else parent


__all__ = [
    "PubchemData",
    "TitleAndSummary",
    "RelatedRecords",
    "ChemicalAndPhysicalProperties",
    "DrugAndMedicationInformation",
    "PharmacologyAndBiochemistry",
    "SafetyAndHazards",
    "Toxicity",
    "AssociatedDisordersAndDiseases",
    "Literature",
    "NamesAndIdentifiers",
    "BiomolecularInteractionsAndPathways",
    "Classification",
]
