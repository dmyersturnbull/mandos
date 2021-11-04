import regex


def _compile(p: str) -> regex.Pattern:
    return regex.compile(p, flags=regex.V1)


class Patterns:
    ghs_code = _compile(r"((?:H\d+)(?:\+H\d+)*)")
    ghs_code_singles = _compile(r"(H\d+)")
    pubchem_compound_url = _compile(r"^https:\/\/pubchem\.ncbi\.nlm\.nih\.gov\/compound\/(.+)$")
    atc_codes = _compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?")
    mesh_codes = _compile(r"[A-Z]")
    # "gm" means gram
    mg_per_kg_pattern = _compile(r"([0-9.]+)\s*((?:[munp]g)|(?:gm?))/kg")
    atc_parts_pattern = pat = _compile(r"([A-Z])([0-9]{2})?([A-Z])?([A-Z])?([A-Z])?")
    target_name_abbrev_species_pattern_1 = _compile(r"^(.+?)\(([^)]+)\)+$")
    target_name_abbrev_species_pattern_2 = _compile(r"^ *([^ ]+) +- +(.+)$")


__all__ = ["Patterns"]
