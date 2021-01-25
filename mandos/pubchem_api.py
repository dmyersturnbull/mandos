"""
PubChem querying API.
"""
from __future__ import annotations

import abc
import logging
import time
from urllib.error import HTTPError
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, Union, FrozenSet

import io
import gzip
import orjson
import pandas as pd
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.query_utils import QueryExecutor

from mandos import MandosUtils
from mandos.model.pubchem_data import PubchemData

logger = logging.getLogger("mandos")


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
        data = dict(
            meta=dict(
                timestamp_fetch_started=datetime.now(timezone.utc).astimezone().isoformat(),
                from_lookup=inchikey,
            )
        )
        t0 = time.monotonic_ns()
        cid = self._fetch_compound(inchikey)
        if cid is None:
            return None
        data["record"] = self._fetch_display_data(cid)["Record"]
        external_table_names = {
            "related:pubchem:related_compounds_with_annotation": "compound",
            "drug:clinicaltrials.gov:clinical_trials": "clinicaltrials",
            "pharm:pubchem:reactions": "pathwayreaction",
            "uses:cpdat:uses": "cpdat",
            "tox:chemidplus:acute_effects": "chemidplus",
            "dis:ctd:associated_disorders_and_diseases": "ctd_chemical_disease",
            "lit:pubchem:depositor_provided_pubmed_citations": "pubmed",
            "patent:depositor_provided_patent_identifiers": "patent",
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
        # get index==0 because we only have 1 compound
        data["structure"] = self._fetch_misc_data(cid)["PC_Compounds"][0]
        del [data["structure"]["props"]]  # redundant with props section in record
        data["classifications"] = self._fetch_hierarchies(cid)["hierarchies"]
        t1 = time.monotonic_ns()
        data["meta"]["timestamp_fetch_finished"] = (
            datetime.now(timezone.utc).astimezone().isoformat()
        )
        data["meta"]["fetch_nanos_taken"] = str(t1 - t0)
        self._strip_by_key_in_place(data, "DisplayControls")
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
                return frozenset(resp.req_list_as("IdentifierList.CID", int))
        raise TimeoutError(f"Search for {inchi} using key {key} timed out")

    def _fetch_compound(self, inchikey: Union[int, str]) -> Optional[int]:
        cid = self._fetch_cid(inchikey)
        if cid is None:
            return None
        data = dict(record=self._fetch_display_data(cid)["Record"])
        data = PubchemData(NestedDotDict(data))
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
        hids = {
            "MeSH Tree": 1,
            "ChEBI Ontology": 2,
            "KEGG: Phytochemical Compounds": 5,
            "KEGG: Drug": 14,
            "KEGG: USP": 15,
            "KEGG: Major components of natural products": 69,
            "KEGG: Target-based Classification of Drugs": 22,
            "KEGG: OTC drugs": 25,
            "KEGG: Drug Classes": 96,
            "CAMEO Chemicals": 86,
            "WHO ATC Classification System": 79,
            "Guide to PHARMACOLOGY Target Classification": 92,
            "ChEMBL Target Tree": 87,
            "EPA CPDat Classification": 99,
            "FDA Pharm Classes": 78,
            "ChemIDplus": 84,
        }
        hids = [1, 2, 5, 69, 79, 84, 99, 1112354]
        build_up = []
        for hid in hids:
            url = f"{self._classifications}?format=json&hid={hid}&search_uid_type=cid&search_uid={cid}&search_type=list&response_type=display"
            try:
                data = orjson.loads(self._query(url))
                logger.debug(f"Found data for classifier {hid}, compound {cid}")
                data = data["Hierarchies"]["Hierarchy"][0]
            except HTTPError:
                logger.debug(f"No data for classifier {hid}, compound {cid}")
                data = {}
            build_up.append(data)
        # These list all of the child nodes for each node
        # Some of them are > 1000 items -- they're HUGE
        # We don't expect to need to navigate to children
        self._strip_by_key_in_place(build_up, "ChildID")
        return NestedDotDict(dict(hierarchies=build_up))

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
    "CachingPubchemApi",
    "QueryingPubchemApi",
]
