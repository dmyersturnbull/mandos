import abc
import math
import time
import urllib
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Mapping, NamedTuple, Optional, Sequence
from urllib import request

import decorateme
import regex
from pocketutils.core.chars import Chars
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.enums import FlagEnum
from pocketutils.core.query_utils import QueryExecutor
from pocketutils.tools.common_tools import CommonTools

from mandos.model import Api, CompoundNotFoundError
from mandos.model.settings import QUERY_EXECUTORS, SETTINGS
from mandos.model.utils.setup import logger


class _Prop(NamedTuple):
    kind: str
    source: str


_prefixes = dict(M=1e6, mM=1e3, µM=1, uM=1, nM=1e-3, pM=1e-6, fM=1e-9)

_PREDICTED_PROPERTIES = [
    _Prop("average_mass", "ChemAxon"),
    _Prop("logp", "ALOGPS"),
    _Prop("logs", "ALOGPS"),
    _Prop("solubility", "ALOGPS"),
    _Prop("pka_strongest_acidic", "ChemAxon"),
    _Prop("polar_surface_area", "ChemAxon"),
    _Prop("polarizability", "ChemAxon"),
    _Prop("physiological_charge", "ChemAxon"),
]

_RULES = [
    _Prop("rule_of_five", "ChemAxon"),
    _Prop("ghose_filter", "ChemAxon"),
    _Prop("veber_rule", "ChemAxon"),
    _Prop("mddr_like_rule", "ChemAxon"),
]

_p1 = regex.compile(r"^([0-9.]+ +\(([0-9.]+) *\- *([0-9.]+)\)$", flags=regex.V1)
_p2 = regex.compile(r"^([0-9.]+) +\+\/\- +([0-9.]+)$", flags=regex.V1)


class HmdbCompoundLookupError(CompoundNotFoundError):
    """ """


class ConcentrationBound(NamedTuple):
    mean: float
    lower: float
    upper: float

    @property
    def std(self) -> float:
        return self.upper / 2 - self.lower / 2

    @property
    def is_symmetric(self) -> bool:
        return math.isclose(self.upper - self.mean, self.mean - self.lower)


@dataclass(frozen=True, repr=True, order=True)
class HmdbProperty:
    kind: str
    source: str
    value: str


@dataclass(frozen=True, repr=True, order=True)
class HmdbDisease:
    name: str
    omim_id: str
    n_refs: int


class PersonAge(FlagEnum):
    unknown = ()
    adults = ()
    children = ()


class PersonSex(FlagEnum):
    unknown = ()
    male = ()
    female = ()


@dataclass(frozen=True, repr=True, order=True)
class HmdbConcentration:
    specimen: str
    ages: PersonAge
    sexes: PersonSex
    condition: Optional[str]
    micromolar: Optional[ConcentrationBound]
    mg_per_kg: Optional[ConcentrationBound]

    def __post_init__(self):
        if (self.mg_per_kg is None) + (self.micromolar is None) != 1:
            raise AssertionError(
                f"Provided both micromolar ({self.micromolar})"
                + f" and mg/kg ({self.mg_per_kg}), or neither"
            )

    @cached_property
    def format_value(self) -> str:
        return f"{self._value}{Chars.narrownbsp}{self._unit}"

    @cached_property
    def format_value_pm(self) -> str:
        v, u, s = self._value, self._unit, Chars.narrownbsp
        return f"{v.mean}{Chars.plusminus}{v.std}{s}{u}"

    @cached_property
    def format_value_range(self) -> str:
        v, u, s = self._value, self._unit, Chars.narrownbsp
        return f"{v.mean}{s}({v.lower}{Chars.en}{v.upper}){s}{u}"

    @property
    def _value(self) -> ConcentrationBound:
        if self.mg_per_kg is not None:
            return self.mg_per_kg
        return self.micromolar

    @property
    def _unit(self) -> str:
        if self.mg_per_kg is not None:
            return " mg/kg"
        return " µmol/L"


class HmdbData:
    def __init__(self, data: NestedDotDict):
        self._data = data

    @property
    def cid(self) -> str:
        return self._data.req_as("metabolite.accession", str)

    @property
    def inchi(self) -> str:
        return self._data.req_as("metabolite.inchi", str)

    @property
    def inchikey(self) -> str:
        return self._data.req_as("metabolite.inchikey", str)

    @property
    def smiles(self) -> str:
        return self._data.req_as("metabolite.smiles", str)

    @property
    def cas(self) -> str:
        return self._data.req_as("metabolite.cas_registry_number", str)

    @property
    def drugbank_id(self) -> Optional[str]:
        return self._data.get_as("metabolite.inchikey", str)

    @property
    def pubchem_id(self) -> Optional[str]:
        return self._data.get_as("metabolite.pubchem_compound_id", str)

    @property
    def create_date(self) -> datetime:
        return datetime.fromisoformat(self._data.req_as("metabolite.creation_date", str))

    @property
    def mod_date(self) -> datetime:
        return datetime.fromisoformat(self._data.req_as("metabolite.update_date", str))

    @cached_property
    def predicted_properties(self) -> Sequence[HmdbProperty]:
        data = self._data.get("metabolite.predicted_properties", [])
        return [
            HmdbProperty(kind=x["kind"], source=x["source"], value=x["value"])
            for x in data
            if _Prop(x["kind"], x["source"]) in _PREDICTED_PROPERTIES
        ]

    @cached_property
    def rules(self) -> Mapping[str, bool]:
        data = self._data.get("metabolite.predicted_properties", [])
        return {
            r["kind"]: CommonTools.parse_bool_flex(r["value"])
            for r in data
            if (r["kind"], r["source"]) in _RULES
        }

    @cached_property
    def diseases(self) -> Sequence[HmdbDisease]:
        data = self._data.get_list_as("metabolite.diseases", NestedDotDict)
        return [HmdbDisease(d["name"], d["omim_id"], len(d.get("references", []))) for d in data]

    @cached_property
    def specimens(self) -> Sequence[str]:
        return self._data.get_list_as("metabolite.biological_properties.biospecimen_locations", str)

    @cached_property
    def tissue_locations(self) -> Sequence[str]:
        return self._data.get_list_as("metabolite.biological_properties.tissue_locations", str)

    @cached_property
    def normal_concentrations(self) -> Sequence[HmdbConcentration]:
        data = self._data.get_list_as("metabolite.normal_concentrations", NestedDotDict, [])
        results = []
        for d in data:
            x = self._new_conc(d)
            if x is not None:
                results.append(x)
        return results

    def _new_conc(self, x: NestedDotDict) -> Optional[HmdbConcentration]:
        specimen = x["biospecimen"]
        # both can be "Not Specified"
        ages = {
            "Adult": PersonAge.adults,
            "Children": PersonAge.children,
            "Both": PersonAge.adults | PersonAge.children,
        }.get(x.get_as("subject_age", str, "").split(" ")[0], PersonAge.unknown)
        sexes = {
            "Male": PersonSex.male,
            "Female": PersonSex.female,
            "Both": PersonSex.female | PersonSex.male,
        }.get(x.get_as("subject_sex", str, ""), PersonSex.unknown)
        condition = (
            None
            if x.get("subject_condition") == "Normal"
            else x.get_as("patient_information", str, "")
        )
        value, units = x.get_as("concentration_value", str), x.get_as("concentration_units", str)
        if value is None or len(value) == 0:
            logger.trace(f"Discarding {x} with empty value")
            return None
        if units not in ["uM", "mg/kg"]:
            logger.trace(f"Discarding {x} with units '{units}'")
            return None
        bound = self._parse_conc(value)
        if bound is None:
            logger.warning(f"Could not parse concentration {value} (units: {units})")
            logger.trace(f"Full data: {x}")
            return None
        return HmdbConcentration(
            specimen=specimen,
            ages=ages,
            sexes=sexes,
            condition=condition,
            micromolar=bound if units == "uM" else None,
            mg_per_kg=bound if units == "mg/kg" else None,
        )

    def _parse_conc(self, value: str) -> Optional[ConcentrationBound]:
        m: regex.Match = _p1.fullmatch(value)
        if m is not None:
            return ConcentrationBound(*m.groups())
        m: regex.Match = _p2.fullmatch(value)
        if m is not None:
            v, std = m.groups()
            return ConcentrationBound(v, v - std, v + std)
        return None

    @cached_property
    def abnormal_concentrations(self) -> Sequence[HmdbConcentration]:
        return self._data.get("metabolite.normal_concentrations", [])


@decorateme.auto_repr_str()
class HmdbApi(Api, metaclass=abc.ABCMeta):
    def fetch(self, hmdb_id: str) -> HmdbData:
        raise NotImplementedError()


@decorateme.auto_repr_str()
class QueryingHmdbApi(HmdbApi):
    def __init__(self, executor: QueryExecutor = QUERY_EXECUTORS.hmdb):
        self._executor = executor

    def fetch(self, inchikey_or_hmdb_id: str) -> HmdbData:
        logger.debug(f"Downloading HMDB data for {inchikey_or_hmdb_id}")
        # e.g. https://hmdb.ca/metabolites/HMDB0001925.xml
        cid = None
        if inchikey_or_hmdb_id.startswith("HMDB"):
            cid = inchikey_or_hmdb_id
        else:
            time.sleep(SETTINGS.hmdb_query_delay_min)  # TODO
            url = f"https://hmdb.ca/unearth/q?query={inchikey_or_hmdb_id}&searcher=metabolites"
            try:
                res = urllib.request.urlopen(url)
                url_ = res.geturl()
                logger.trace(f"Got UR {url_} from {url}")
                cid = url_.split("/")[-1]
                if not cid.startswith("HMDB"):
                    raise ValueError(f"Invalid CID {cid} from URL {url_}")
            except Exception:
                raise HmdbCompoundLookupError(f"No HMDB match for {inchikey_or_hmdb_id}")
        url = f"https://hmdb.ca/metabolites/{cid}.xml"
        try:
            data = self._executor(url)
        except Exception:
            raise HmdbCompoundLookupError(f"No HMDB match for {inchikey_or_hmdb_id} ({cid})")
        return HmdbData(self._to_json(data))

    def _to_json(self, xml) -> NestedDotDict:
        response = {}
        for child in list(xml):
            if len(list(child)) > 0:
                response[child.tag] = self._to_json(child)
            else:
                response[child.tag] = child.text or ""
        return NestedDotDict(response)

    def _query(self, url: str) -> str:
        data = self._executor(url)
        tt = self._executor.last_time_taken
        wt, qt = tt.wait.total_seconds(), tt.query.total_seconds()
        bts = int(len(data) * 8 / 1024)
        logger.trace(f"Queried {bts} kb from {url} in {qt:.1} s with {wt:.1} s of wait")
        return data


@decorateme.auto_repr_str()
class CachingHmdbApi(HmdbApi):
    def __init__(
        self, query: Optional[QueryingHmdbApi], cache_dir: Path = SETTINGS.hmdb_cache_path
    ):
        self._query = query
        self._cache_dir = cache_dir

    def path(self, inchikey_or_hmdb_id: str) -> Path:
        return self._cache_dir / f"{inchikey_or_hmdb_id}.json.gz"

    def fetch(self, inchikey_or_hmdb_id: str) -> HmdbData:
        path = self.path(inchikey_or_hmdb_id)
        if path.exists():
            return HmdbData(NestedDotDict.read_json(path))
        else:
            data = self._query.fetch(inchikey_or_hmdb_id)
            path = self.path(data.cid)
            data._data.write_json(path, mkdirs=True)
            logger.info(f"Saved HMDB metabolite {data.cid}")
            self._write_links(data)
            return data

    def _write_links(self, data: HmdbData) -> None:
        path = self.path(data.cid)
        # these all have different prefixes, so it's ok
        aliases = [
            data.inchikey,
            *[ell for ell in [data.cas, data.pubchem_id, data.drugbank_id] if ell is not None],
        ]
        for alias in aliases:
            link = self.path(alias)
            link.unlink(missing_ok=True)
            path.link_to(link)
        logger.debug(f"Added aliases {','.join([str(s) for s in aliases])} ⇌ {data.cid} ({path})")


__all__ = [
    "HmdbApi",
    "QueryingHmdbApi",
    "CachingHmdbApi",
    "HmdbProperty",
    "ConcentrationBound",
    "HmdbData",
    "PersonSex",
    "PersonAge",
    "HmdbConcentration",
    "HmdbDisease",
    "HmdbCompoundLookupError",
]
