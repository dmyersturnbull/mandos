"""
PubChem data.
"""
from __future__ import annotations

import abc
import logging
import time
import re
import enum
from datetime import date, datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Dict, Union, FrozenSet, Any
from typing import Tuple as Tup

import io
import gzip
import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor
from pocketutils.tools.string_tools import StringTools

from mandos import MandosResources, MandosUtils
from mandos.model.query_utils import JsonNavigator, Fns, FilterFn

logger = logging.getLogger("mandos")
hazards = pd.read_csv(MandosResources.path("hazards.tab"), sep="\t")
hazards = dict(hazards.set_index("code").T.to_dict())


class Misc:
    empty_frozenset = frozenset([])


class Patterns:
    ghs_code = re.compile(r"((?:H\d+)(?:\+H\d+)*)")
    ghs_code_singles = re.compile(r"(H\d+)")
    pubchem_compound_url = re.compile(r"^https:\/\/pubchem\.ncbi\.nlm\.nih\.gov\/compound\/(.+)$")
    atc_codes = re.compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?")
    mesh_codes = re.compile(r"[A-Z]")


class Code(str):
    @property
    def type_name(self) -> str:
        return self.__class__.__name__.lower()


class CodeTypes:
    """
    These turn out to be extremely useful for documenting return types.
    For example, ``DrugbankInteraction`` might have a ``gene`` field,
    which can be described as a ``GenecardSymbol`` if known.
    """

    class EcNumber(Code):
        """
        e.g. 'EC:4.6.1.1'
        """

    class GeneId(Code):
        """
        GeneCard, UniProt gene name, etc.
        e.g. 'slc1a2'
        """

    class GenecardSymbol(GeneId):
        """"""

    class PubchemCompoundId(Code):
        """
        e.g. 2352
        """

        @property
        def value(self) -> int:
            return int(self)

    class MeshCode(Code):
        """"""

    class PdbId(Code):
        """"""

    class MeshHeading(Code):
        """"""

    class MeshSubheading(Code):
        """"""

    class DeaSchedule(Code):
        """"""

        @property
        def value(self) -> int:
            return Fns.roman_to_arabic(1, 5)(self)

    class GhsCode(Code):
        """"""


class CoOccurrenceType(enum.Enum):
    chemical = enum.auto()
    gene = enum.auto()
    disease = enum.auto()

    @property
    def x_name(self) -> str:
        if self is CoOccurrenceType.chemical:
            return "ChemicalNeighbor"
        elif self is CoOccurrenceType.gene:
            return "ChemicalGeneSymbolNeighbor"
        elif self is CoOccurrenceType.disease:
            return "ChemicalDiseaseNeighbor"
        raise AssertionError(f"{self} not found!!")

    @property
    def id_name(self) -> str:
        if self is CoOccurrenceType.chemical:
            return "CID"
        elif self is CoOccurrenceType.gene:
            return "GeneSymbol"
        elif self is CoOccurrenceType.disease:
            return "MeSH"
        raise AssertionError(f"{self} not found!!")


@dataclass(frozen=True, repr=True, eq=True)
class ClinicalTrial:
    title: str
    conditions: FrozenSet[str]
    phase: str
    status: str
    interventions: FrozenSet[str]
    cids: FrozenSet[int]
    source: str

    @property
    def known_phase(self) -> int:
        return {
            "Phase 4": 4,
            "Phase 3": 3,
            "Phase 2": 2,
            "Phase 1": 1,
            "Early Phase 1": 1,
            "N/A": 0,
        }.get(self.status, 0)


@dataclass(frozen=True, repr=True, eq=True)
class GhsCode:
    code: CodeTypes.GhsCode
    statement: str
    clazz: str
    categories: FrozenSet[str]
    signal_word: str
    type: str

    @classmethod
    def find(cls, code: str) -> GhsCode:
        h = hazards[code]
        cats = h["category"]  # TODO
        return GhsCode(
            code=CodeTypes.GhsCode(code),
            statement=h["statement"],
            clazz=h["class"],
            categories=cats,
            signal_word=h["signal_word"],
            type=h["type"],
        )

    @property
    def level(self) -> int:
        return int(self.code[1])


@dataclass(frozen=True, repr=True, eq=True)
class AssociatedDisorder:
    disease: str
    evidence_type: str
    n_refs: int


@dataclass(frozen=True, repr=True, eq=True)
class AtcCode:
    code: str
    name: str

    @property
    def level(self) -> int:
        return len(self.parts)

    @property
    def parts(self) -> Sequence[str]:
        pat = re.compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?")
        match = pat.fullmatch(self.code)
        return [g for g in match.groups() if g is not None]


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankInteraction:
    action: str
    target: str
    gene: str
    function: str
    n_refs: int


@dataclass(frozen=True, repr=True, eq=True)
class DrugbankDdi:
    is_active: bool
    micromolar: float
    activity_type: str
    target: str


@dataclass(frozen=True, repr=True, eq=True)
class PubchemBioassay:
    drug: str
    interaction: str


@dataclass(frozen=True, repr=True, eq=True)
class PdbEntry:
    pdbid: str
    title: str
    exp_method: str
    resolution: float
    lig_names: FrozenSet[str]
    cids: FrozenSet[int]
    uniprot_ids: FrozenSet[str]
    pmids: FrozenSet[str]
    dois: FrozenSet[str]


@dataclass(frozen=True, repr=True, eq=True)
class PubmedEntry:
    pmid: int
    article_type: str
    pmidsrcs: FrozenSet[str]
    mesh_headings: FrozenSet[CodeTypes.MeshHeading]
    mesh_subheadings: FrozenSet[CodeTypes.MeshSubheading]
    mesh_codes: FrozenSet[CodeTypes.MeshCode]
    cids: FrozenSet[int]
    article_title: str
    article_abstract: str
    journal_name: str
    pub_date: date


@dataclass(frozen=True, repr=True, eq=True)
class Publication:
    pmid: int
    pub_date: date
    is_review: bool
    title: str
    journal: str
    relevance_score: int


@dataclass(frozen=True, repr=True, eq=True)
class CoOccurrence:
    neighbor_id: str
    neighbor_name: str
    kind: CoOccurrenceType
    # https://pubchemdocs.ncbi.nlm.nih.gov/knowledge-panels
    article_count: int
    query_article_count: int
    neighbor_article_count: int
    score: int
    publications: FrozenSet[Publication]


@dataclass(frozen=True, repr=True, eq=True)
class DrugGeneInteraction:
    gene_name: Optional[str]
    gene_claim_id: Optional[str]
    source: str
    interactions: FrozenSet[str]
    pmids: FrozenSet[int]
    dois: FrozenSet[str]


@dataclass(frozen=True, repr=True, eq=True)
class CompoundGeneInteraction:
    gene_name: Optional[str]
    interactions: FrozenSet[str]
    tax_name: str
    pmids: FrozenSet[int]


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
        if self._data["Record.RecordType"] != "CID":
            raise ValueError(
                "RecordType for {} is {}".format(
                    self._data["Record.RecordNumber"], self._data["Record.RecordType"]
                )
            )
        return self._data["Record.RecordNumber"]

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
        return JsonNavigator.create(self._data) / "Record"

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
            // Fns.require_only()
        )
        parent = parent / Fns.extract_group_1(r"CID (\d+) +.*") / int // Fns.request_only()
        return self.cid if parent.get is None else parent.get


class ChemicalAndPhysicalProperties(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Chemical and Physical Properties"

    @property
    def computed(self) -> Mapping[Tup[str, str], str]:
        props = {
            dot["TOCHeading"]: dot["Information"]
            for dot in (self._mini / "Computed Properties" / "Section").get
        }
        dct: Dict[Tup[str, str], str] = {}
        for heading, info in props.items():
            for dot in info:
                try:
                    dot = NestedDotDict(dot)
                    if "Reference" in dot:
                        ref = ",".join(dot["Reference"])
                        if "Value" in dot and "Number" in dot["Value"]:
                            num = ",".join([str(q) for q in dot["Value"]["Number"]])
                            value = num.strip() + " " + dot.get_as("Value.Unit", str, "")
                            dct[(heading, ref)] = value.replace("\n", "").replace("\r", "").strip()
                except (KeyError, ValueError):
                    logger.debug(f"Failed on {dot}")
                    raise
        return dct


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
            >> Fns.join_nonnulls()
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
            >> Fns.join_nonnulls()
        ).get

    @property
    def classes(self) -> FrozenSet[str]:
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
    def dea_schedule(self) -> Optional[CodeTypes.DeaSchedule]:
        return (
            self.mini
            / "DEA Controlled Substances"
            / "Information"
            / self._has_ref("Drug Enforcement Administration (DEA)")
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Fns.require_only()
            / Fns.extract_group_1(r" *Schedule ([IV]+).*")
            / CodeTypes.DeaSchedule
            // Fns.request_only()
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
                trial["title"],
                frozenset(trial["conditions"].split("|")),
                trial["phase"],
                trial["status"],
                frozenset(trial["interventions"].split("|")),
                frozenset([int(z) for z in trial["cids"].split("|")]),
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
            >> Fns.join_nonnulls()
        ).get

    @property
    def summary_ncit_text(self) -> Optional[str]:
        return (
            self._mini
            / "Pharmacology"
            / "Information"
            / self._has_ref("NCI Thesaurus (NCIt)")
            / Fns.key_equals("Name", "Pharmacology")
            / "Value"
            / "StringWithMarkup"
            >> "String"
            >> Fns.join_nonnulls()
        ).get

    @property
    def summary_ncit_links(self) -> FrozenSet[str]:
        return (
            self._mini
            / "Pharmacology"
            / "Information"
            / self._has_ref("NCI Thesaurus (NCIt)")
            / Fns.key_equals("Name", "Pharmacology")
            / "Value"
            / "StringWithMarkup"
            / "Markup"
            / Fns.key_equals("Type", "PubChem Internal Link")
            // ["URL"]
            // Fns.require_only()
            / Fns.extract_group_1(Patterns.pubchem_compound_url)
            / Fns.lowercase_unless_acronym()  # TODO necessary but unfortunate -- cocaine and Cocaine
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
            / Fns.key_equals("Name", "ATC Code")
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
            >> Fns.request_only()
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
            / Fns.key_equals("Type", "PubChem Internal Link")
            // ["URL"]
            // Fns.require_only()
            / Fns.extract_group_1(Patterns.pubchem_compound_url)
            / Fns.lowercase_unless_acronym()  # TODO necessary but unfortunate -- cocaine and Cocaine
        ).to_set

    @property
    def biochem_reactions(self) -> FrozenSet[str]:
        # TODO from multiple sources
        return (self._tables / "pathwayreaction" >> "name").to_set


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
            / Fns.key_equals("Name", "GHS Hazard Statements")
            / "Value"
            / "StringWithMarkup"
            // ["String"]
            // Fns.require_only()
            / Fns.extract_group_1(r"^(H\d+)[ :].*$")
            // Fns.split_and_flatten_nonnulls("+")
        ).get
        return frozenset([GhsCode.find(code) for code in codes])


class Toxicity(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Toxicity"

    @property
    def acute_effects(self) -> FrozenSet[str]:
        values = (
            self._tables
            / "chemidplus"
            // ["effect"]
            // Fns.request_only()
            // Fns.split_and_flatten_nonnulls(";", skip_nulls=True)
        ).contents
        return frozenset(
            {
                v.strip().lower().replace("\n", " ").replace("\r", " ").replace("\t", " ")
                for v in values
            }
        )


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
            // ["diseasename", "directevidence", "dois"]
            / [Fns.identity, Fns.identity, Fns.n_bar_items]
            // AssociatedDisorder
        ).to_set


class Literature(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Literature"

    @property
    def depositor_pubmed_articles(self) -> FrozenSet[PubmedEntry]:
        def split_mesh_headings(s: str) -> FrozenSet[CodeTypes.MeshHeading]:
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

        def split_mesh_subheadings(s: Optional[str]) -> FrozenSet[CodeTypes.MeshSubheading]:
            if s is None:
                return Misc.empty_frozenset
            return frozenset({k.strip() for k in s.split(",") if k.strip() != ""})

        def split_mesh_codes(s: Optional[str]) -> FrozenSet[CodeTypes.MeshCode]:
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

        def get_date(s: Optional[str]) -> Optional[date]:
            if s is None:
                return None
            return datetime.strptime(str(s).strip(), "%Y%m%d").date()

        keys = {
            "pmid": Fns.req_is_int,
            "articletype": Fns.req_is_str,
            "pmidsrcs": split_sources,
            "meshheadings": split_mesh_headings,
            "meshsubheadings": split_mesh_subheadings,
            "meshcodes": split_mesh_codes,
            "cids": split_cids,
            "articletitle": get_text,
            "articleabstract": get_text,
            "articlejourname": get_text,
            "articlepubdate": get_date,
        }
        entries = (
            self._tables
            / "pubmed"
            // list(keys.keys())
            / list(keys.values())
            // Fns.construct(PubmedEntry)
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
            if kind is CoOccurrenceType.chemical:
                neighbor_id = CodeTypes.PubchemCompoundId(neighbor_id)
            elif kind is CoOccurrenceType.gene and neighbor_id.startswith("EC:"):
                neighbor_id = CodeTypes.EcNumber(neighbor_id)
            elif kind is CoOccurrenceType.gene and re.compile("^[a-z][a-z0-9.]+$").fullmatch(
                neighbor_id
            ):
                neighbor_id = CodeTypes.GeneId(neighbor_id)
            elif kind is CoOccurrenceType.disease:
                pass
            else:
                raise ValueError(f"Could not find ID type for {kind} ID {neighbor_id}")
            evidence = link["Evidence"][kind.x_name]
            neighbor_name = evidence["NeighborName"]
            ac = evidence["ArticleCount"]
            nac = evidence["NeighborArticleCount"]
            qac = evidence["QueryArticleCount"]
            score = evidence["CooccurrenceScore"]
            articles = [NestedDotDict(k) for k in evidence["Article"]]
            pubs = {
                Publication(
                    pmid=pub.req_as("PMID", int),
                    pub_date=datetime.strptime(pub["PublicationDate"].strip(), "%Y-%m-%d").date(),
                    is_review=pub["IsReview"],
                    title=pub["Title"].strip(),
                    journal=pub["Journal"],
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

    @property
    def drug_gene_interactions(self) -> FrozenSet[DrugGeneInteraction]:
        # the order of this dict is crucial
        keys = {
            "genename": Fns.str_id_or_none,
            "geneclaimname": Fns.str_id_or_none,
            "interactionclaimsource": Fns.req_is_str_or_none,
            "interactiontypes": Fns.split_bars("|"),
            "pmids": Fns.split_bars_to_int(","),
            "dois": Fns.split_bars("|"),
        }
        return (
            self._tables
            / "dgidb"
            // list(keys.keys())
            / list(keys.values())
            // Fns.construct(DrugGeneInteraction)
        ).to_set

    @property
    def compound_gene_interactions(self) -> FrozenSet[CompoundGeneInteraction]:
        # the order of this dict is crucial
        keys = {
            "genesymbol": CodeTypes.GenecardSymbol,
            "interactionclaimsource": Fns.req_is_str_or_none,
            "tax_id": Fns.req_is_str,
            "interaction": Fns.split_bars("|"),
            "pmids": Fns.split_bars_to_int(
                "|"
            ),  # YES, this really is different from the , used in DrugGeneInteraction
        }
        return (
            self._tables
            / "ctdchemicalgene"
            // list(keys.keys())
            / list(keys.values())
            // Fns.construct(CompoundGeneInteraction)
        ).to_set

    @property
    def drugbank_interactions(self) -> FrozenSet[DrugbankInteraction]:
        raise NotImplementedError()

    @property
    def drugbank_ddis(self) -> FrozenSet[DrugbankDdi]:
        raise NotImplementedError()

    @property
    def bioassay(self) -> FrozenSet[DrugbankDdi]:
        raise NotImplementedError()


class BiomolecularInteractionsAndPathways(PubchemMiniDataView):
    """"""

    @property
    def _whoami(self) -> str:
        return "Biomolecular Interactions and Pathways"


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
        return self._data.get("Record.RecordTitle")

    @property
    def title_and_summary(self) -> TitleAndSummary:
        return TitleAndSummary(self._data)

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
    def classification(self) -> Classification:
        return Classification(self._data)

    @property
    def parent_or_self(self) -> int:
        parent = self.related_records.parent
        return self.cid if parent is None else parent


class PubchemApi(metaclass=abc.ABCMeta):
    def fetch_data_from_cid(self, cid: int) -> Optional[PubchemData]:
        # separated from fetch_data to make it completely clear what an int value means
        # noinspection PyTypeChecker
        return self.fetch_data(cid)

    def fetch_data(self, inchikey: str) -> Optional[PubchemData]:
        raise NotImplementedError()

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        raise NotImplementedError()


class QueryingPubchemApi(PubchemApi):
    def __init__(self):
        self._query = QueryExecutor(0.22, 0.25)

    _pug = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    _pug_view = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
    _sdg = "https://pubchem.ncbi.nlm.nih.gov/sdq/sdqagent.cgi"
    _classifications = "https://pubchem.ncbi.nlm.nih.gov/classification/cgi/classifications.fcgi"
    _link_db = "https://pubchem.ncbi.nlm.nih.gov/link_db/link_db_server.cgi"

    def fetch_data(self, inchikey: str) -> Optional[PubchemData]:
        cid = self._fetch_compound(inchikey)
        if cid is None:
            return None
        data = dict(self._fetch_display_data(cid))
        external_table_names = {
            "related:pubchem:related_compounds_with_annotation": "compound",
            "drug:clinicaltrials.gov:clinical_trials": "clinicaltrials",
            "pharm:pubchem:reactions": "pathwayreaction",
            "uses:cpdat:uses": "cpdat",
            "tox:chemidplus:acute_effects": "chemidplus",
            "dis:ctd:associated_disorders_and_diseases": "ctd_chemical_disease",
            "lit:pubchem:depositor_provided_pubmed_citations": "pubmed",
            "bio:rcsb_pdb:protein_bound_3d_structures": "pdb",
            "bio:dgidb:drug_gene_interactions": "dgidb",
            "bio:ctd:chemical_gene_interactions": "ctdchemicalgene",
            "bio:drugbank:drugbank_interactions": "drugbank",
            "bio:drugbank:drug_drug_interactions": "drugbankddi",
            "bio:pubchem:bioassay_results": "bioactivity",
        }
        external_link_set_names = {
            "lit:pubchem:chemical_cooccurrences_in_literature": "ChemicalNeighbor",
            "lit:pubchem:gene_cooccurrences_in_literature": "ChemicalGeneSymbolNeighbor",
            "lit:pubchem:disease_cooccurrences_in_literature": "ChemicalDiseaseNeighbor",
        }
        data["external_tables"] = {
            table: self._fetch_external_table(cid, table) for table in external_table_names.values()
        }
        data["link_sets"] = {
            table: self._fetch_external_link_set(cid, table)
            for table in external_link_set_names.values()
        }
        data["misc_data"] = self._fetch_misc_data(cid)
        data["classifications"] = self._fetch_hierarchies(cid)
        return PubchemData(NestedDotDict(data))

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        slash = self._query_and_type(inchi)
        req = self._query(
            f"{self._pug}/compound/similarity/{slash}/{inchi}/JSON?Threshold={min_tc}",
            method="post",
        )
        key = orjson.loads(req)["Waiting"]["ListKey"]
        t0 = time.monotonic()
        while time.monotonic() - t0 < 5:
            # it'll wait as needed here
            resp = self._query(f"{self._pug}/compound/listkey/{key}/cids/JSON")
            resp = NestedDotDict(orjson.loads(resp))
            if resp.get("IdentifierList.CID") is not None:
                return resp.get_list_as("IdentifierList.CID", int)
        raise TimeoutError(f"Search for {inchi} using key {key} timed out")

    def _fetch_compound(self, inchikey: Union[int, str]) -> Optional[int]:
        cid = self._fetch_cid(inchikey)
        if cid is None:
            return None
        data = self._fetch_display_data(cid)
        data = PubchemData(data)
        return data.parent_or_self

    def _fetch_cid(self, inchikey: str) -> Optional[int]:
        # The PubChem API docs LIE!!
        # Using ?cids_type=parent DOES NOT give the parent
        # Ex: https://pubchem.ncbi.nlm.nih.gov/compound/656832
        # This is cocaine HCl, which has cocaine (446220) as a parent
        # https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/656832/JSON
        # gives 656832 back again
        # same thing when querying by inchikey
        slash = self._query_and_type(inchikey)
        url = f"{self._pug}/compound/{slash}/JSON"
        data = self._query_json(url)
        found = [x["id"]["id"] for x in data["PC_Compounds"]]
        if len(found) == 0:
            return None
        elif len(found) > 1:
            logger.warning(
                f"Found {len(found)} CIDs for {inchikey}: {found}. Using first ({found[0]})."
            )
        found = found[0]["cid"]
        assert isinstance(found, int), f"Type of {found} is {type(found)}"
        return found

    def _fetch_display_data(self, cid: int) -> Optional[NestedDotDict]:
        url = f"{self._pug_view}/data/compound/{cid}/JSON/?response_type=display"
        return self._query_json(url)

    def _fetch_misc_data(self, cid: int) -> Optional[NestedDotDict]:
        url = f"{self._pug}/compound/cid/{cid}/JSON"
        return self._query_json(url)

    def _query_json(self, url: str) -> NestedDotDict:
        data = self._query(url)
        data = NestedDotDict(orjson.loads(data))
        if "Fault" in data:
            raise ValueError(f"Request failed ({data.get('Code')}) on {url}: {data.get('Message')}")
        return data

    def _fetch_external_link_set(self, cid: int, table: str) -> NestedDotDict:
        url = f"{self._link_db}?format=JSON&type={table}&operation=GetAllLinks&id_1={cid}"
        data = self._query(url)
        return NestedDotDict(orjson.loads(data))

    def _fetch_hierarchies(self, cid: int) -> NestedDotDict:
        url = f"{self._classifications}?format=json&search_uid_type=cid&search_uid={cid}&search_type=list"
        data = self._query(url)
        return NestedDotDict(orjson.loads(data))

    def _fetch_external_table(self, cid: int, table: str) -> Sequence[dict]:
        url = self._external_table_url(cid, table)
        data = self._query(url)
        df: pd.DataFrame = pd.read_csv(io.StringIO(data))
        return list(df.T.to_dict().values())

    def _external_table_url(self, cid: int, collection: str) -> str:
        return (
            self._sdg
            + "?infmt=json"
            + "&outfmt=csv"
            + "&query={ download : * , collection : "
            + collection
            + " , where :{ ands :[{ cid : "
            + str(cid)
            + " }]}}"
        ).replace(" ", "%22")

    def _query_and_type(self, inchi: Union[int, str], req_full: bool = False) -> str:
        allowed = ["cid", "inchi", "smiles"] if req_full else ["cid", "inchi", "inchikey", "smiles"]
        if isinstance(inchi, int):
            return f"cid/{inchi}"
        else:
            query_type = MandosUtils.get_query_type(inchi).name.lower()
            if query_type not in allowed:
                raise ValueError(f"Can't query {inchi} with type {query_type}")
            return f"{query_type}/{inchi}"


class CachingPubchemApi(PubchemApi):
    def __init__(self, cache_dir: Path, querier: QueryingPubchemApi, compress: bool = True):
        self._cache_dir = cache_dir
        self._querier = querier
        self._compress = compress

    def fetch_data(self, inchikey: str) -> Optional[PubchemData]:
        path = self.data_path(inchikey)
        if not path.exists():
            data = self._querier.fetch_data(inchikey)
            path.parent.mkdir(parents=True, exist_ok=True)
            encoded = data.to_json()
            self._write_json(encoded, path)
            return data
        read = self._read_json(path)
        return PubchemData(read)

    def _write_json(self, encoded: str, path: Path) -> None:
        if self._compress:
            path.write_bytes(gzip.compress(encoded.encode(encoding="utf8")))
        else:
            path.write_text(encoded, encoding="utf8")

    def _read_json(self, path: Path) -> NestedDotDict:
        if self._compress:
            deflated = gzip.decompress(path.read_bytes())
            read = orjson.loads(deflated)
        else:
            read = orjson.loads(path.read_text(encoding="utf8"))
        return NestedDotDict(read)

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        path = self.similarity_path(inchi)
        if not path.exists():
            df = None
            existing = set()
        else:
            df = pd.read_csv(path, sep="\t")
            df = df[df["min_tc"] < min_tc]
            existing = set(df["cid"].values)
        if len(existing) == 0:
            found = self._querier.find_similar_compounds(inchi, min_tc)
            path.parent.mkdir(parents=True, exist_ok=True)
            new_df = pd.DataFrame([pd.Series(dict(cid=cid, min_tc=min_tc)) for cid in found])
            if df is not None:
                new_df = pd.concat([df, new_df])
            new_df.to_csv(path, sep="\t")
            return frozenset(existing.union(found))
        else:
            return frozenset(existing)

    def data_path(self, inchikey: str):
        ext = ".json.gz" if self._compress else ".json"
        return self._cache_dir / "data" / f"{inchikey}{ext}"

    def similarity_path(self, inchikey: str):
        ext = ".tab.gz" if self._compress else ".tab"
        return self._cache_dir / "similarity" / f"{inchikey}{ext}"


__all__ = [
    "PubchemApi",
    "PubchemData",
    "CachingPubchemApi",
    "QueryingPubchemApi",
    "ClinicalTrial",
    "AssociatedDisorder",
    "AtcCode",
    "DrugbankInteraction",
    "DrugbankDdi",
    "PubchemBioassay",
    "DrugGeneInteraction",
    "CompoundGeneInteraction",
    "PubmedEntry",
    "Code",
    "CodeTypes",
    "CoOccurrenceType",
    "CoOccurrence",
    "Publication",
]
