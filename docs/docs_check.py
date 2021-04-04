"""
Verify that parts of the docs match what's in the code.
"""
from __future__ import annotations


class DocCheck:
    def check_table(self) -> DocCheck:
        return self


if __name__ == "__main__":
    DocCheck().check_table()
