"""
Temporary caching of search results as they progress.
"""
from pathlib import Path
from typing import Iterator, Sequence

import decorateme
import orjson
from pocketutils.core.exceptions import PathExistsError

from mandos import logger
from mandos.model.settings import SETTINGS


@decorateme.auto_repr_str()
class SearchCache:
    def __init__(self, path: Path, compounds: Sequence[str], *, restart: bool, proceed: bool):
        self._path = path
        exists = self._path.exists() and self._meta_path.exists()
        if exists:
            self._data = orjson.loads(self._meta_path.read_text(encoding="utf8"))
            if "done" not in self._data:
                logger.warning(f"Invalid progress file {self._meta_path}; restarting")
                exists = False
        if not exists:
            self._data = dict(path=str(self.path), done=set())
            logger.debug(f"Starting fresh cache for {self.path}")
        elif exists and restart:
            logger.caution(f"Replacing {path} with {self.at} processed compounds")
            self._data["done"] = set()
        elif exists and proceed:
            logger.caution(f"Resuming {path} with {self.at} processed compounds")
        elif exists:
            raise PathExistsError(f"{path} already exists with {self.at} processed compounds")
        self.save()  # must write -- divisible by 0
        self._queue: Iterator[str] = iter([c for c in compounds if c not in self._data["done"]])

    def next(self) -> str:
        return next(self._queue)

    def save(self, *compounds: str) -> None:
        if isinstance(self._data["done"], list):  # TODO
            self._data["done"] = set(self._data["done"])
        for c in compounds:
            self._data["done"].add(c)
        if self.at % SETTINGS.save_every == 0:
            dat = {k: (list(v) if isinstance(v, set) else v) for k, v in self._data.items()}
            dat = orjson.dumps(dat).decode(encoding="utf8")
            self._meta_path.write_text(dat, encoding="utf8")
            logger.debug(f"Saved to {self._meta_path}")

    @property
    def path(self) -> Path:
        return self._path

    @property
    def at(self) -> int:
        return len(self._data["done"])

    @property
    def _meta_path(self) -> Path:
        return self._path.parent / ("." + self._path.name + ".progress.json.tmp")

    def kill(self) -> None:
        self._data = None
        if self._meta_path.exists():
            self._meta_path.unlink()
            logger.debug(f"Destroyed search cache {self._meta_path}")


__all__ = ["SearchCache"]
