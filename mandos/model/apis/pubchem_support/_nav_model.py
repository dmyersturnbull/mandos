from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class FilterFn:
    keep_if: Callable[[Any], bool]

    def __call__(self, *args, **kwargs):
        return self.keep_if(*args, **kwargs)


__all__ = ["FilterFn"]
