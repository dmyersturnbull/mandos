"""
API for finding similar compounds.
"""
from __future__ import annotations

import abc
from typing import FrozenSet

import decorateme

from mandos.model import Api


@decorateme.auto_repr_str()
class SimilarityApi(Api, metaclass=abc.ABCMeta):
    def search(self, inchi: str, min_tc: float) -> FrozenSet[int]:
        raise NotImplementedError()


__all__ = ["SimilarityApi"]
