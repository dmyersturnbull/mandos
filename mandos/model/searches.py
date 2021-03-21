from __future__ import annotations
import abc
import dataclasses
import logging
import typing
from typing import Generic, Sequence, TypeVar

import pandas as pd

from mandos.model.hits import AbstractHit, HitFrame
from mandos.model import CompoundNotFoundError

logger = logging.getLogger("mandos")

H = TypeVar("H", bound=AbstractHit, covariant=True)


class Search(Generic[H], metaclass=abc.ABCMeta):
    """
    Something to search and how to do it.
    """

    def __init__(self, key: str):
        self.key = key

    @property
    def search_class(self) -> str:
        return self.__class__.__name__

    @property
    def search_name(self) -> str:
        return self.__class__.__name__.lower().replace("search", "")

    @property
    def data_source(self) -> str:
        raise NotImplementedError()

    def get_params(self) -> typing.Mapping[str, typing.Any]:
        return {key: value for key, value in vars(self).items() if not key.startswith("_")}

    def find_to_df(self, inchikeys: Sequence[str]) -> HitFrame:
        hits = self.find_all(inchikeys)
        return HitFrame([pd.Series({f: getattr(h, f) for f in self.hit_fields()}) for h in hits])

    def find_all(self, inchikeys: Sequence[str]) -> Sequence[H]:
        """
        Loops over every compound and calls ``find``.
        Just comes with better logging.

        Args:
            inchikeys:

        Returns:

        """
        lst = []
        for i, compound in enumerate(inchikeys):
            try:
                x = self.find(compound)
            except CompoundNotFoundError:
                logger.error(f"Failed to find compound {compound}. Skipping.")
                continue
            lst.extend(x)
            logger.debug(f"Found {len(x)} {self.search_name} annotations for {compound}")
            if i > 0 and i % 20 == 0 or i == len(inchikeys) - 1:
                logger.info(
                    f"Found {len(lst)} {self.search_name} annotations for {i} of {len(inchikeys)} compounds"
                )
        return lst

    def find(self, inchikey: str) -> Sequence[H]:
        """
        To override.

        Args:
            inchikey:

        Returns:
            Something

        Raises:
            CompoundNotFoundError
        """
        raise NotImplementedError()

    @classmethod
    def hit_fields(cls) -> Sequence[str]:
        """
        Gets the fields in the Hit type parameter.

        Returns:

        """
        # Okay, there's a lot of magic going on here
        # We need to access the _parameter_ H on cls -- raw `H` doesn't work
        # get_args and __orig_bases__ do this for us
        # then dataclasses.fields gives us the dataclass fields
        # there's also actual_h.__annotations__, but that doesn't include ClassVar and InitVar
        # (not that we're using those)
        # If this magic is too magical, we can make this an abstract method
        # But that would be a lot of excess code and it might be less modular
        actual_h = typing.get_args(cls.get_h())[0]
        return [f.name for f in dataclasses.fields(actual_h)]

    @classmethod
    def get_h(cls):
        """
        What is my hit type?

        Returns:

        """
        # noinspection PyUnresolvedReferences
        return cls.__orig_bases__[0]

    def __repr__(self) -> str:
        return ", ".join([k + "=" + str(v) for k, v in self.get_params()])

    def __str__(self) -> str:
        return repr(self)

    def __eq__(self, other: Search) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(f"{type(other)} not comparable")
        return repr(self) == repr(other)


__all__ = ["Search", "HitFrame"]
