import abc
from random import Random
from typing import TypeVar

from mandos.model.hits import AbstractHit
from mandos.model.searches import Search

H = TypeVar("H", bound=AbstractHit, covariant=True)


class MetaSearch(Search[H], metaclass=abc.ABCMeta):
    def __init__(self, key: str, seed: int):
        self.seed = seed
        self.random = Random(seed)
        super().__init__(key)


__all__ = ["MetaSearch"]
