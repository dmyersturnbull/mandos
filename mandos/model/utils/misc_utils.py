from datetime import datetime
from typing import Sequence, TypeVar

import pint
from pint import Quantity
from pint.errors import PintTypeError
from suretime import Suretime


_UNIT_REG = pint.UnitRegistry()
T = TypeVar("T", covariant=True)


class MiscUtils:
    """
    These are here to make sure I always use the same NTP server, etc.
    """

    @classmethod
    def canonicalize_quantity(cls, s: str, dimensionality: str) -> Quantity:
        """
        Returns a quantity in reduced units from a magnitude with units.

        Args:
            s: The string to parse; e.g. ``"1 m/s^2"``.
               Unit names and symbols permitted, and spaces may be omitted.
            dimensionality: The resulting Quantity is check against this;
                            e.g. ``"[length]/[meter]^2"``

        Returns:
            a pint ``Quantity``

        Raise:
            PintTypeError: If the dimensionality is inconsistent
        """
        q = _UNIT_REG.Quantity(s).to_reduced_units()
        if not q.is_compatible_with(dimensionality):
            raise PintTypeError(f"{s} not of dimensionality {dimensionality}")
        return q

    @classmethod
    def utc(cls) -> datetime:
        return Suretime.tagged.now_utc_sys().dt

    @classmethod
    def serialize_list(cls, lst: Sequence[str]) -> str:
        return " || ".join([str(x) for x in lst])

    @classmethod
    def deserialize_list(cls, s: str) -> Sequence[str]:
        return s.split(" || ")


__all__ = ["MiscUtils"]
