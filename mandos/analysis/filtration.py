"""
Tool to filter annotations.
"""
from __future__ import annotations

from pathlib import Path

from pocketutils.core.dot_dict import NestedDotDict

from mandos.model.hits import HitFrame


class Filtration:
    @classmethod
    def from_file(cls, path: Path) -> Filtration:
        raise NotImplementedError()

    @classmethod
    def from_toml(cls, dot: NestedDotDict) -> Filtration:
        raise NotImplementedError()

    def apply(self, df: HitFrame) -> HitFrame:
        raise NotImplementedError()


__all__ = ["Filtration"]
