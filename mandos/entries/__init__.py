from pathlib import Path
from typing import Optional

from mandos import MandosLogging


class EntryMeta:
    @classmethod
    def set_logging(cls, verbose: bool, quiet: bool, log: Optional[Path]) -> str:
        if verbose and quiet:
            raise ValueError(f"Cannot set both --quiet and --verbose")
        elif quiet:
            level = "ERROR"
        elif verbose:
            level = "INFO"
        else:
            level = "WARNING"
        MandosLogging.set_log_level(level, log)
        return level


__all__ = ["EntryMeta"]
