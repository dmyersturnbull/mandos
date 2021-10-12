"""
Temporary caching of search results as they progress.
"""
from pathlib import Path
from typing import Iterator, Sequence

import orjson
from suretime import Suretime

from mandos import logger
from mandos.model.settings import SETTINGS


class SearchCache:
    def __init__(self, path: Path, compounds: Sequence[str]):
        self._path = path
        if self._meta_path.exists():
            self._data = orjson.loads(self._meta_path.read_text(encoding="utf8", errors="strict"))
            logger.caution(f"Resuming {path} with {self.at} completed compounds")
        else:
            self._data = dict(
                start=Suretime.tagged.now_utc_sys().iso, last=None, path=str(self.path), done=set()
            )
            logger.debug(f"Starting fresh cache for {path}")
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
            dat = orjson.dumps(dat).decode(encoding="utf8", errors="utf8")
            self._meta_path.write_text(dat, encoding="utf8", errors="strict")
            logger.debug(f"Saved to {self._meta_path}")

    @property
    def path(self) -> Path:
        return self._path

    @property
    def at(self) -> int:
        return len(self._data["done"])

    @property
    def _meta_path(self) -> Path:
        return self._path.parent / ("." + self._path.name + ".meta.json.tmp")

    def kill(self) -> None:
        self._data = None
        self._meta_path.unlink()
        logger.debug(f"Destroyed search cache {self._meta_path}")


__all__ = ["SearchCache"]
