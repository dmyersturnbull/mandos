from pathlib import Path, PurePath
from typing import Union


def get_test_resource(*nodes: Union[PurePath, str]) -> Path:
    """Gets a path of a test resource file under resources/."""
    p = Path(__file__).parent
    while p.name != "mandos":
        p = p.parent
    return Path(p, "resources", *nodes)


__all__ = ["get_test_resource"]
