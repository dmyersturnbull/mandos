from __future__ import annotations

import abc
import dataclasses
from datetime import datetime
from typing import Generic, Mapping, Sequence, TypeVar, Union

from pocketutils.core.exceptions import XTypeError
from pocketutils.tools.reflection_tools import ReflectionTools
from suretime import Suretime

from mandos.model.hit_dfs import HitDf
from mandos.model.hits import AbstractHit
from mandos.model.utils.setup import MandosResources

H = TypeVar("H", bound=AbstractHit, covariant=True)


class SearchError(Exception):
    """
    Wrapper for any exception raised in ``find`` except for ``CompoundNotFoundError``.
    """

    def __init__(
        self,
        *args,
        inchikey: str = None,
        search_key: str = None,
        search_class: str = None,
        **kwargs,
    ):
        super().__init__(*args, *kwargs)
        self.inchikey = inchikey
        self.search_key = search_key
        self.search_class = search_class


class Search(Generic[H], metaclass=abc.ABCMeta):
    """
    Something to search and how to do it.
    """

    def __init__(self, key: str):
        self.key = key

    @classmethod
    def primary_data_source(cls) -> str:
        z = MandosResources.from_memory("strings")[cls.__name__]["source"]
        # TODO: really?
        return z.split(":")[0]

    @property
    def search_class(self) -> str:
        return self.__class__.__name__

    @classmethod
    def search_name(cls) -> str:
        return cls.__name__.lower().replace("search", "")

    def get_params(self) -> Mapping[str, Union[None, str, int, float, datetime]]:
        """
        Returns the *parameters* of this ``Search`` their values.
        Parameters are attributes that do not begin with an underscore.
        """
        return {
            key: value
            for key, value in vars(self).items()
            if not key.startswith("_") and key not in ["api", "key"]
        }

    def find(self, inchikey: str) -> Sequence[H]:
        # override this
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
        # noinspection PyDataclass
        return [f.name for f in dataclasses.fields(x) if f.name != "search_class"]

    @classmethod
    def get_h(cls):
        """
        Returns the underlying hit TypeVar, ``H``.
        """
        # noinspection PyTypeChecker
        return ReflectionTools.get_generic_arg(cls, AbstractHit)

    def _format_source(self, **kwargs) -> str:
        s = MandosResources.from_memory("strings")[self.search_class]["source"]
        for k, v in kwargs.items():
            s = s.replace(f"{{{k}}}", str(v))
        return s

    def _format_predicate(self, **kwargs) -> str:
        s = MandosResources.from_memory("strings")[self.search_class]["predicate"]
        for k, v in kwargs.items():
            s = s.replace(f"{{{k}}}", str(v))
        return s

    def _create_hit(
        self,
        c_origin: str,
        c_matched: str,
        c_id: str,
        c_name: str,
        data_source: str,
        predicate: str,
        object_id: str,
        object_name: str,
        **kwargs,
    ) -> H:
        # ignore statement -- we've removed it for now
        entry = dict(
            record_id=None,
            search_key=self.key,
            search_class=self.search_class,
            data_source=data_source,
            run_date=Suretime.tagged.now_utc_sys().iso_with_zone,
            cache_date=None,
            weight=1,
            compound_id=c_id,
            origin_inchikey=c_origin,
            matched_inchikey=c_matched,
            compound_name=c_name,
            predicate=predicate,
            object_id=object_id,
            object_name=object_name,
        )
        entry.update(kwargs)
        clazz = self.__class__.get_h()
        # noinspection PyArgumentList
        return clazz(**entry)

    def __repr__(self) -> str:
        return ", ".join([k + "=" + str(v) for k, v in self.get_params().items()])

    def __str__(self) -> str:
        return repr(self)

    def __eq__(self, other: Search) -> bool:
        """
        Returns True iff all of the parameters match, thereby excluding attributes with underscores.
        Multiversal equality.

        Raises:
            TypeError: If ``other`` is not a :class:`Search`
        """
        if not isinstance(other, Search):
            raise XTypeError(f"{type(other)} not comparable")
        return repr(self) == repr(other)


__all__ = ["Search", "HitDf", "SearchError"]
