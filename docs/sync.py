"""
Verify that parts of the docs match what's in the code.
"""
from __future__ import annotations

from pathlib import Path

_root = (Path(__file__).parent.parent / "mandos").absolute()


class DocSync:
    def fix_api(self) -> DocSync:
        for py in _root.glob("**/*.py"):
            fixed = (
                "   mandos."
                + (
                    str(py.relative_to(_root).with_suffix(""))
                    .replace("/", ".")
                    .replace("\\", ".")
                    .replace("__init__", "")
                )
            ).rstrip(".")
            print(fixed)
        return self


if __name__ == "__main__":
    DocSync().fix_api()
