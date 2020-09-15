from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional, Set

logger = logging.getLogger("mandos")


@total_ordering
@dataclass()
class AtcCode:
    """
    An ATC code node in the tree.
    """

    record: str
    description: str
    level: int
    parent: AtcCode
    children: Set[AtcCode]

    def traverse_to(self, level: int) -> Optional[AtcCode]:
        """

        Args:
            level:

        Returns:

        """
        if level < 1:
            raise ValueError(f"Level {level} < 1")
        if self.level == level:
            return self
        elif self.level < level:
            return self.parent.traverse_to(level)
        else:
            return None

    def __hash__(self):
        return hash(self.record)

    def __eq__(self, other: AtcCode) -> bool:
        """

        Args:
            other:

        Returns:

        """
        if not isinstance(other, AtcCode):
            raise TypeError(f"{type(other)} is not an AtcCode")
        return self.record == other.record

    def __lt__(self, other: AtcCode):
        """

        Args:
            other:

        Returns:

        """
        if not isinstance(other, AtcCode):
            raise TypeError(f"{type(other)} is not an AtcCode")
        return self.record < other.record


__all__ = ["AtcCode"]
