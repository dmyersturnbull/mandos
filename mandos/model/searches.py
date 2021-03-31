from __future__ import annotations
import abc
import dataclasses
import typing
from typing import Generic, Sequence, TypeVar

import pandas as pd

from mandos import logger
from mandos.model.hits import AbstractHit, HitFrame
from mandos.model import CompoundNotFoundError, ReflectionUtils

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
        """
        Where the data originally came from; e.g. ``the Human Metabolome Database (HMDB)``"
        """
        raise NotImplementedError()

    def get_params(self) -> typing.Mapping[str, typing.Any]:
        """
        Returns the *parameters* of this ``Search`` their values.
        Parameters are attributes that do not begin with an underscore.
        """
        return {key: value for key, value in vars(self).items() if not key.startswith("_")}

    def find_to_df(self, inchikeys: Sequence[str]) -> HitFrame:
        """
        Calls :py:meth:`find_all` and returns a :py:class:`HitFrame` DataFrame subclass.
        Writes a logging ERROR for each compound that was not found.

        Args:
            inchikeys: A list of InChI key strings
        """
        hits = self.find_all(inchikeys)
        return HitFrame([pd.Series({f: getattr(h, f) for f in self.hit_fields()}) for h in hits])

    def find_all(self, inchikeys: Sequence[str]) -> Sequence[H]:
        """
        Loops over every compound and calls ``find``.
        Comes with better logging.
        Writes a logging ERROR for each compound that was not found.

        Args:
            inchikeys: A list of InChI key strings

        Returns:
            The list of :py:class:`mandos.model.hits.AbstractHit`
        """
        lst = []
        for i, compound in enumerate(inchikeys):
            try:
                x = self.find(compound)
            except CompoundNotFoundError:
                logger.error(f"NOT FOUND: {compound}. Skipping.")
                continue
            except Exception:
                logger.error(f"Failed on {compound}", exc_info=True)
                continue
            lst.extend(x)
            logger.debug(f"Found {len(x)} {self.search_name} annotations for {compound}")
        logger.info(
            f"Found {len(lst)} {self.search_name} annotations for {i} of {len(inchikeys)} compounds"
        )
        return lst

    def find(self, inchikey: str) -> Sequence[H]:
        """
        To override.
        Finds the annotations for a single compound.

        Args:
            inchikey: An InChI Key

        Returns:
            A list of annotations

        Raises:
            CompoundNotFoundError
        """
        raise NotImplementedError()

    @classmethod
    def hit_fields(cls) -> Sequence[str]:
        """
        Gets the fields in the Hit type parameter.
        """
        # Okay, there's a lot of magic going on here
        # We need to access the _parameter_ H on cls -- raw `H` doesn't work
        # get_args and __orig_bases__ do this for us
        # then dataclasses.fields gives us the dataclass fields
        # there's also actual_h.__annotations__, but that doesn't include ClassVar and InitVar
        # (not that we're using those)
        # If this magic is too magical, we can make this an abstract method
        # But that would be a lot of excess code and it might be less modular
        x = cls.get_h()
        actual_h = x.__bases__[0]
        return [f.name for f in dataclasses.fields(actual_h)]

    @classmethod
    def get_h(cls):
        """
        Returns the underlying hit TypeVar, ``H``.
        """
        return ReflectionUtils.get_generic_arg(cls, AbstractHit)

    def __repr__(self) -> str:
        return ", ".join([k + "=" + str(v) for k, v in self.get_params().items()])

    def __str__(self) -> str:
        return repr(self)

    def __eq__(self, other: Search) -> bool:
        """
        Returns True iff all of the parameters match, thereby excluding attributes with underscores.
        Multiversal equality.

        Raises:
            TypeError: If ``other`` is not a :py:class:`Search`
        """
        if not isinstance(other, Search):
            raise TypeError(f"{type(other)} not comparable")
        return repr(self) == repr(other)


__all__ = ["Search", "HitFrame"]
