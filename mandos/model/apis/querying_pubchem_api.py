"""
PubChem querying API.
"""
from __future__ import annotations

import io
import time
from datetime import datetime, timezone
from typing import FrozenSet, Mapping, Optional, Sequence, Union, Any
from urllib.error import HTTPError

import orjson
import regex
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor

from mandos import logger
from mandos.model.apis.pubchem_api import PubchemApi, PubchemCompoundLookupError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.settings import QUERY_EXECUTORS


class QueryingPubchemApi(PubchemApi):
    def __init__(
        self,
        chem_data: bool = False,
        extra_tables: bool = False,
        classifiers: bool = False,
        extra_classifiers: bool = False,
        executor: QueryExecutor = QUERY_EXECUTORS.pubchem,
    ):
        self._use_chem_data = chem_data
        self._use_extra_tables = extra_tables
        self._use_classifiers = classifiers
        self._use_extra_classifiers = extra_classifiers
        self._executor = executor

    _pug = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    _pug_view = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
    _sdg = "https://pubchem.ncbi.nlm.nih.gov/sdq/sdqagent.cgi"
    _classifications = "https://pubchem.ncbi.nlm.nih.gov/classification/cgi/classifications.fcgi"
    _link_db = "https://pubchem.ncbi.nlm.nih.gov/link_db/link_db_server.cgi"

    def find_inchikey(self, cid: int) -> str:
        # return self.fetch_data(cid).names_and_identifiers.inchikey
        props = self.fetch_properties(cid)
        return props["InChIKey"]

    def find_id(self, inchikey: str) -> Optional[int]:
        # we have to scrape to get the parent anyway,
        # so just download it
        # TODO: there's a faster way
        try:
            return self.fetch_data(inchikey).cid
        except PubchemCompoundLookupError:
            logger.debug(f"Could not find pubchem ID for {inchikey}", exc_info=True)
            return None

    def fetch_properties(self, cid: int) -> Mapping[str, Any]:
        url = f"{self._pug}/compound/cid/{cid}/JSON"
        #
        try:
            matches: NestedDotDict = self._query_json(url)
        except HTTPError:
            raise PubchemCompoundLookupError(f"Failed finding pubchem compound {cid}")
        props = matches["PC_Compounds"][0]["props"]
        props = {NestedDotDict(p).get("urn.label"): p.get("value") for p in props}

        def _get_val(v):
            v = NestedDotDict(v)
            for t in ["ival", "fval", "sval"]:
                if t in v.keys():
                    return v[t]

        props = {k: _get_val(v) for k, v in props.items() if k is not None and v is not None}
        return props

    def fetch_data(self, inchikey: Union[str, int]) -> [PubchemData]:
        # Dear God this is terrible
        # Here are the steps:
        # 1. Download HTML for the InChI key and scrape the CID
        # 2. Download the "display" JSON data from the CID
        # 3. Look for a Parent-type related compound. If it exists, download its display data
        # 4. Download the structural data and append it
        # 5. Download the external table CSVs and append them
        # 6. Download the link sets and append them
        # 7. Download the classifiers (hierarchies) and append them
        # 8. Attach metadata about how we found this.
        # 9. Return the stupid, stupid result as a massive JSON struct.
        logger.info(f"Downloading PubChem data for {inchikey}")
        if isinstance(inchikey, int):
            cid = inchikey
            # note: this might not be the parent
            # that's ok -- we're about to fix that
            inchikey = self.find_inchikey(cid)
        else:
            cid = self._scrape_cid(inchikey)
        data = self._fetch_data(cid, inchikey)
        data = self._get_parent(cid, inchikey, data)
        return data

    def find_similar_compounds(self, inchi: Union[int, str], min_tc: float) -> FrozenSet[int]:
        req = self._executor(
            f"{self._pug}/compound/similarity/inchikey/{inchi}/JSON?Threshold={min_tc}",
            method="post",
        )
        key = orjson.loads(req)["Waiting"]["ListKey"]
        t0 = time.monotonic()
        while time.monotonic() - t0 < 5:
            # it'll wait as needed here
            resp = self._executor(f"{self._pug}/compound/listkey/{key}/cids/JSON")
            resp = NestedDotDict(orjson.loads(resp))
            if resp.get("IdentifierList.CID") is not None:
                return frozenset(resp.req_list_as("IdentifierList.CID", int))
        raise TimeoutError(f"Search for {inchi} using key {key} timed out")

    def _scrape_cid(self, inchikey: str) -> int:
        # This is awful
        # Every attempt to get the actual, correct, unique CID corresponding to the inchikey
        # failed with every proper PubChem API
        # We can't use <pug_view>/data/compound/<inchikey> -- we can only use a CID there
        # I found it with a PUG API
        # https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/CID/GJSURZIOUXUGAL-UHFFFAOYSA-N/record/JSON
        # But that returns multiple results!!
        # There's no apparent way to find out which one is real
        # I tried then querying each found CID, getting the display data, and looking at their parents
        # Unfortunately, we end up with multiple contradictory parents
        # Plus, that's insanely slow -- we have to get the full JSON data for each parent
        # Every worse -- the PubChem API docs LIE!!
        # Using ?cids_type=parent DOES NOT GIVE THE PARENT compound
        # Ex: https://pubchem.ncbi.nlm.nih.gov/compound/656832
        # This is cocaine HCl, which has cocaine (446220) as a parent
        # https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/656832/JSON
        # gives 656832 back again
        # same thing when querying by inchikey
        # Ultimately, I found that I can get HTML containing the CID from an inchikey
        # From there, we'll just have to download its "display" data and get the parent, then download that data
        url = f"https://pubchem.ncbi.nlm.nih.gov/compound/{inchikey}"
        pat = regex.compile(
            r'<meta property="og:url" content="https://pubchem\.ncbi\.nlm\.nih\.gov/compound/(\d+)">',
            flags=regex.V1,
        )
        try:
            html = self._executor(url)
        except HTTPError:
            raise PubchemCompoundLookupError(
                f"Failed finding pubchem compound (HTML) from {inchikey} [url: {url}]"
            )
        match = pat.search(html)
        if match is None:
            raise ValueError(f"Something is wrong with the HTML from {url}; og:url not found")
        return int(match.group(1))

    def _get_parent(self, cid: int, inchikey: str, data: PubchemData) -> PubchemData:
        # guard with is not None: we're not caching, so don't do it twice
        if data.parent_or_none is None:
            return data
        try:
            return self._fetch_data(data.parent_or_none, inchikey)
        except HTTPError:
            raise PubchemCompoundLookupError(
                f"Failed finding pubchem parent compound (JSON)"
                f"for cid {data.parent_or_none}, child cid {cid}, inchikey {inchikey}"
            )

    def _fetch_data(self, cid: int, inchikey: str) -> PubchemData:
        when_started = datetime.now(timezone.utc).astimezone()
        t0 = time.monotonic_ns()
        try:
            data = self._fetch_core_data(cid)
        except HTTPError:
            raise PubchemCompoundLookupError(
                f"Failed finding pubchem compound (JSON) from cid {cid}, inchikey {inchikey}"
            )
        t1 = time.monotonic_ns()
        when_finished = datetime.now(timezone.utc).astimezone()
        data["meta"] = self._get_metadata(inchikey, when_started, when_finished, t0, t1)
        self._strip_by_key_in_place(data, "DisplayControls")
        return PubchemData(NestedDotDict(data))

    def _fetch_core_data(self, cid: int) -> dict:
        return dict(
            record=self._fetch_display_data(cid),
            structure=self._fetch_structure_data(cid),
            external_tables=self._fetch_external_tables(cid),
            link_sets=self._fetch_external_linksets(cid),
            classifications=self._fetch_hierarchies(cid),
            properties=NestedDotDict(self.fetch_properties(cid)),
        )

    def _get_metadata(self, inchikey: str, started: datetime, finished: datetime, t0: int, t1: int):
        return dict(
            timestamp_fetch_started=started.isoformat(),
            timestamp_fetch_finished=finished.isoformat(),
            from_lookup=inchikey,
            fetch_nanos_taken=str(t1 - t0),
        )

    def _fetch_display_data(self, cid: int) -> Optional[NestedDotDict]:
        url = f"{self._pug_view}/data/compound/{cid}/JSON/?response_type=display"
        return self._query_json(url)["Record"]

    def _fetch_structure_data(self, cid: int) -> NestedDotDict:
        if not self._use_chem_data:
            return NestedDotDict({})
        url = f"{self._pug}/compound/cid/{cid}/JSON"
        data = self._query_json(url)["PC_Compounds"][0]
        del [data["structure"]["props"]]  # redundant with props section in record
        return data

    def _fetch_external_tables(self, cid: int) -> Mapping[str, str]:
        return {
            ext_table: self._fetch_external_table(cid, ext_table)
            for ext_table in self._tables_to_use.values()
        }

    def _fetch_external_linksets(self, cid: int) -> Mapping[str, str]:
        return {
            table: self._fetch_external_linkset(cid, table)
            for table in self._linksets_to_use.values()
        }

    def _fetch_hierarchies(self, cid: int) -> NestedDotDict:
        build_up = {}
        for hname, hid in self._hierarchies_to_use.items():
            try:
                build_up[hname] = self._fetch_hierarchy(cid, hid)
            except (HTTPError, KeyError, LookupError) as e:
                logger.debug(f"No data for classifier {hid}, compound {cid}: {e}")
        # These list all of the child nodes for each node
        # Some of them are > 1000 items -- they're HUGE
        # We don't expect to need to navigate to children
        self._strip_by_key_in_place(build_up, "ChildID")
        return NestedDotDict(build_up)

    def _fetch_external_table(self, cid: int, table: str) -> Sequence[dict]:
        url = self._external_table_url(cid, table)
        data = self._executor(url)
        df: pd.DataFrame = pd.read_csv(io.StringIO(data))
        # TODO: UserWarning: DataFrame columns are not unique, some columns will be omitted.
        return list(df.T.to_dict().values())

    def _fetch_external_linkset(self, cid: int, table: str) -> NestedDotDict:
        url = f"{self._link_db}?format=JSON&type={table}&operation=GetAllLinks&id_1={cid}"
        data = self._executor(url)
        return NestedDotDict(orjson.loads(data))

    def _fetch_hierarchy(self, cid: int, hid: int) -> Sequence[dict]:
        url = f"{self._classifications}?format=json&hid={hid}&search_uid_type=cid&search_uid={cid}&search_type=list&response_type=display"
        data: Sequence[dict] = orjson.loads(self._executor(url))["Hierarchies"]
        # underneath Hierarchies is a list of Hierarchy
        logger.debug(f"Found data for classifier {hid}, compound {cid}")
        if len(data) == 0:
            raise LookupError(f"Failed getting hierarchy {hid}")
        return data

    @property
    def _tables_to_use(self) -> Mapping[str, str]:
        dct = {
            "drug:clinicaltrials.gov:clinical_trials": "clinicaltrials",
            "pharm:pubchem:reactions": "pathwayreaction",
            "uses:cpdat:uses": "cpdat",
            "tox:chemidplus:acute_effects": "chemidplus",
            "dis:ctd:associated_disorders_and_diseases": "ctd_chemical_disease",
            "lit:pubchem:depositor_provided_pubmed_citations": "pubmed",
            "bio:dgidb:drug_gene_interactions": "dgidb",
            "bio:ctd:chemical_gene_interactions": "ctdchemicalgene",
            "bio:drugbank:drugbank_interactions": "drugbank",
            "bio:drugbank:drug_drug_interactions": "drugbankddi",
            "bio:pubchem:bioassay_results": "bioactivity",
        }
        if self._use_extra_tables:
            dct.update(
                {
                    "patent:depositor_provided_patent_identifiers": "patent",
                    "bio:rcsb_pdb:protein_bound_3d_structures": "pdb",
                    "related:pubchem:related_compounds_with_annotation": "compound",
                }
            )
        return dct

    @property
    def _linksets_to_use(self) -> Mapping[str, str]:
        return {
            "lit:pubchem:chemical_cooccurrences_in_literature": "ChemicalNeighbor",
            "lit:pubchem:gene_cooccurrences_in_literature": "ChemicalGeneSymbolNeighbor",
            "lit:pubchem:disease_cooccurrences_in_literature": "ChemicalDiseaseNeighbor",
        }

    @property
    def _hierarchies_to_use(self) -> Mapping[str, int]:
        if not self._use_classifiers:
            return {}
        dct = {
            "MeSH Tree": 1,
            "ChEBI Ontology": 2,
            "WHO ATC Classification System": 79,
            "Guide to PHARMACOLOGY Target Classification": 92,
            "ChEMBL Target Tree": 87,
        }
        if self._use_extra_classifiers:
            dct.update(
                {
                    "KEGG: Phytochemical Compounds": 5,
                    "KEGG: Drug": 14,
                    "KEGG: USP": 15,
                    "KEGG: Major components of natural products": 69,
                    "KEGG: Target-based Classification of Drugs": 22,
                    "KEGG: OTC drugs": 25,
                    "KEGG: Drug Classes": 96,
                    "CAMEO Chemicals": 86,
                    "EPA CPDat Classification": 99,
                    "FDA Pharm Classes": 78,
                    "ChemIDplus": 84,
                }
            )
        return dct

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

    def _query_json(self, url: str) -> NestedDotDict:
        data = self._executor(url)
        data = NestedDotDict(orjson.loads(data))
        if "Fault" in data:
            raise ValueError(f"Request failed ({data.get('Code')}) on {url}: {data.get('Message')}")
        return data

    def _strip_by_key_in_place(self, data: Union[dict, list], bad_key: str) -> None:
        if isinstance(data, list):
            for x in data:
                self._strip_by_key_in_place(x, bad_key)
        elif isinstance(data, dict):
            for k, v in list(data.items()):
                if k == bad_key:
                    del data[k]
                elif isinstance(v, (list, dict)):
                    self._strip_by_key_in_place(v, bad_key)


__all__ = ["QueryingPubchemApi"]
