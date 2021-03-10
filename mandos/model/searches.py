import abc
import dataclasses
import logging
import typing
from typing import Generic, Sequence, TypeVar

from mandos.model.hits import AbstractHit
from mandos.model import CompoundNotFoundError

logger = logging.getLogger("mandos")

H = TypeVar("H", bound=AbstractHit, covariant=True)


class Search(Generic[H], metaclass=abc.ABCMeta):
    """
    Something to search and how to do it.
    """

    @property
    def search_name(self) -> str:
        return self.__class__.__name__.lower().replace("search", "")

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


__all__ = ["Search"]
