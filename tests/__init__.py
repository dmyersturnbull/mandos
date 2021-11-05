from pathlib import Path, PurePath
from typing import Union


def get_test_resource(*nodes: Union[PurePath, str]) -> Path:
    """Gets a path of a test resource file under resources/."""
    p = Path(__file__).parent
    # the parent of the root is itself -- for some reason
    while p.name != "mandos" and p != p.parent:
        p = p.parent
    return Path(p, "resources", *nodes)


__all__ = ["get_test_resource"]
