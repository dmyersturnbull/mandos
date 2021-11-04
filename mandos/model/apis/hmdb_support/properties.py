from typing import NamedTuple


class _Prop(NamedTuple):
    kind: str
    source: str


PREDICTED_PROPERTIES = [
    _Prop("average_mass", "ChemAxon"),
    _Prop("logp", "ALOGPS"),
    _Prop("logs", "ALOGPS"),
    _Prop("solubility", "ALOGPS"),
    _Prop("pka_strongest_acidic", "ChemAxon"),
    _Prop("polar_surface_area", "ChemAxon"),
    _Prop("polarizability", "ChemAxon"),
    _Prop("physiological_charge", "ChemAxon"),
]

RULES = [
    _Prop("rule_of_five", "ChemAxon"),
    _Prop("ghose_filter", "ChemAxon"),
    _Prop("veber_rule", "ChemAxon"),
    _Prop("mddr_like_rule", "ChemAxon"),
]


__all__ = ["_Prop", "PREDICTED_PROPERTIES", "RULES"]
