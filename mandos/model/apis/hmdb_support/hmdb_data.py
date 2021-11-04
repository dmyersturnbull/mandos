import math
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from typing import Mapping, NamedTuple, Optional, Sequence

import regex
from pocketutils.core.chars import Chars
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.enums import FlagEnum
from pocketutils.tools.common_tools import CommonTools

from mandos.model.apis.hmdb_support.properties import PREDICTED_PROPERTIES, RULES, _Prop
from mandos.model.utils.setup import logger

_prefixes = dict(M=1e6, mM=1e3, µM=1, uM=1, nM=1e-3, pM=1e-6, fM=1e-9)
_p1 = regex.compile(r"^([0-9.]+) +\(([0-9.]+) *\- *([0-9.]+)\)$", flags=regex.V1)
_p2 = regex.compile(r"^([0-9.]+) +\+\/\- +([0-9.]+)$", flags=regex.V1)


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
            if _Prop(x["kind"], x["source"]) in PREDICTED_PROPERTIES
        ]

    @cached_property
    def rules(self) -> Mapping[str, bool]:
        data = self._data.get("metabolite.predicted_properties", [])
        return {
            r["kind"]: CommonTools.parse_bool_flex(r["value"])
            for r in data
            if (r["kind"], r["source"]) in RULES
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


__all__ = [
    "HmdbProperty",
    "ConcentrationBound",
    "HmdbData",
    "PersonSex",
    "PersonAge",
    "HmdbConcentration",
    "HmdbDisease",
]
