from pathlib import Path

from pocketutils.tools.filesys_tools import FilesysTools

from mandos.model.utils.setup import logger


def unlink(path: Path, *, missing_ok: bool = False) -> None:
    info = FilesysTools.get_info(path)
    path.unlink(missing_ok=missing_ok)
    if info.is_valid_symlink:
        logger.trace(f"Deleted valid symlink {path} (to {info.resolved})")
    elif info.is_broken_symlink:
        logger.trace(f"Deleted -broken- symlink {path} (to {info.resolved})")
    elif info.is_file:
        logger.trace(f"Deleted file {path}")
    elif info.source.exists():  # can't happen, I think
        logger.trace(f"Deleted misc. path {path}")
    else:
        logger.trace(f"Did not delete {path} (did not exist)")


__all__ = ["unlink"]
