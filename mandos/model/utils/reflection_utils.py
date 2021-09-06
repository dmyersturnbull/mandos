import inspect
import sys
import typing
from typing import Type, Optional, Mapping, Any


T = typing.TypeVar("T")


class InjectionError(LookupError):
    """ """


class ReflectionUtils:
    @classmethod
    def get_generic_arg(cls, clazz: Type[T], bound: Optional[Type[T]] = None) -> Type:
        """
        Finds the generic argument (specific TypeVar) of a :py:class:`~typing.Generic` class.
        **Assumes that ``clazz`` only has one type parameter. Always returns the first.**

        Args:
            clazz: The Generic class
            bound: If non-None, requires the returned type to be a subclass of ``bound`` (or equal to it)

        Returns:
            The class

        Raises:
            AssertionError: For most errors
        """
        bases = clazz.__orig_bases__
        try:
            param = typing.get_args(bases[0])[0]
        except KeyError:
            raise AssertionError(f"Failed to get generic type on {cls}")
        if not issubclass(param, bound):
            raise AssertionError(f"{param} is not a {bound}")
        return param

    @classmethod
    def subclass_dict(cls, clazz: Type[T], concrete: bool = False) -> Mapping[str, Type[T]]:
        return {c.__name__: c for c in cls.subclasses(clazz, concrete=concrete)}

    @classmethod
    def subclasses(cls, clazz, concrete: bool = False):
        for subclass in clazz.__subclasses__():
            yield from cls.subclasses(subclass, concrete=concrete)
            if (
                not concrete
                or not inspect.isabstract(subclass)
                and not subclass.__name__.startswith("_")
            ):
                yield subclass

    @classmethod
    def default_arg_values(cls, func) -> Mapping[str, Optional[Any]]:
        return {k: v.default for k, v in cls.optional_args(func).items()}

    @classmethod
    def required_args(cls, func):
        """
        Finds parameters that lack default values.

        Args:
            func: A function or method

        Returns:
            A dict mapping parameter names to instances of ``MappingProxyType``,
            just as ``inspect.signature(func).parameters`` does.
        """
        return cls._args(func, True)

    @classmethod
    def optional_args(cls, func):
        """
        Finds parameters that have default values.

        Args:
            func: A function or method

        Returns:
            A dict mapping parameter names to instances of ``MappingProxyType``,
            just as ``inspect.signature(func).parameters`` does.
        """
        return cls._args(func, False)

    @classmethod
    def _args(cls, func, req):
        signature = inspect.signature(func)
        return {
            k: v
            for k, v in signature.parameters.items()
            if req
            and v.default is inspect.Parameter.empty
            or not req
            and v.default is not inspect.Parameter.empty
        }

    @classmethod
    def injection(cls, fully_qualified: str, clazz: Type[T]) -> Type[T]:
        """
        Gets a **class** by its fully-resolved class name.

        Args:
            fully_qualified:
            clazz:

        Returns:
            The Type

        Raises:
            InjectionError: If the class was not found
        """
        s = fully_qualified
        mod = s[: s.rfind(".")]
        clz = s[s.rfind(".") :]
        try:
            return getattr(sys.modules[mod], clz)
        except AttributeError:
            raise InjectionError(
                f"Did not find {clazz} by fully-qualified class name {fully_qualified}"
            ) from None
