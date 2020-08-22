from __future__ import annotations

from pathlib import Path, PurePath
from typing import Any, Mapping, Optional, Sequence, Union

import tomlkit


class NestedDotDict:
    """A thin wrapper around toml to make getting values easier."""

    @classmethod
    def read_toml(cls, path: Union[PurePath, str]) -> NestedDotDict:
        return NestedDotDict(tomlkit.loads(Path(path).read_text(encoding="utf8")))

    def __init__(self, x: Mapping[str, Any]) -> None:
        self._x = x

    def sub(self, items: str) -> NestedDotDict:
        return NestedDotDict(self.get(items, {}))

    def bool(self, items: str, default: Optional[bool] = None) -> Optional[bool]:
        return bool(self.get(items, default))

    def int(self, items: str, default: Optional[int] = None) -> Optional[int]:
        return int(self.get(items, default))

    def float(self, items: str, default: Optional[float] = None) -> Optional[float]:
        return float(self.get(items, default))

    def str(self, items: str, default: Optional[str] = None) -> Optional[str]:
        return self.get(items, default)

    def path(self, items: str, default: Optional[Path] = None) -> Optional[Path]:
        return Path(self.get(items, default))

    def str_list(self, items: str) -> Sequence[str]:
        return self.get(items, [])

    def int_list(self, items: str) -> Sequence[int]:
        return [int(s) for s in self.get(items, [])]

    def float_list(self, items: str) -> Sequence[int]:
        return [float(s) for s in self.get(items, [])]

    def get(self, items: str, default=None):
        at = self._x
        for item in items.split("."):
            at = at[item]
        return self._x.get(items, default)

    def __getitem__(self, items: str):
        at = self._x
        for item in items.split("."):
            at = at[item]
        return at

    def __repr__(self):
        return str(self._x)

    def __str__(self):
        return str(self._x)

    def __eq__(self, other):
        return str(self) == str(other)


__all__ = ["NestedDotDict"]
