import re
from pathlib import Path
from typing import Mapping

from mandos.model import MandosResources


class RegexMap:
    def __init__(self, dct: Mapping[re.Pattern, str]):
        self._dct = dct

    def get(self, s: str) -> str:
        for pat, fixed in self._dct.items():
            sub = pat.sub(fixed, s)
            if sub != s:
                return sub
        return s


class RegexMapParser:
    @classmethod
    def from_resource(cls, name: str):
        return cls.from_path(MandosResources.path("mappings", name, suffix=".regexes"))

    @classmethod
    def from_path(cls, path: Path):
        dct = {}
        for line in path.read_text(encoding="utf8").splitlines():
            if not line.startswith("#"):
                key, value = line.split("--->")
                key, value = key.strip(), value.strip()
                dct[re.compile(key)] = value
        return RegexMap(dct)


if __name__ == "__main__":
    mp = RegexMapParser.from_resource("@targets_neuro.regex")
    print(mp.get("Dopamine D3 receptor"))


__all__ = ["RegexMap", "RegexMapParser"]
