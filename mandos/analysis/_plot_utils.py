"""

"""
from __future__ import annotations

import enum
from pathlib import Path
from typing import Any, Generator, Mapping, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import Colormap, LinearSegmentedColormap, ListedColormap, to_hex
from matplotlib.figure import Figure
from pocketutils.core.dot_dict import NestedDotDict
from pocketutils.core.enums import CleverEnum
from pocketutils.core.exceptions import BadCommandError, LengthError, LookupFailedError
from pocketutils.tools.common_tools import CommonTools

# noinspection PyProtectedMember
from pocketutils.tools.unit_tools import UnitTools
from seaborn.palettes import SEABORN_PALETTES
from typeddfs import TypedDfs

from mandos.model.utils import MandosResources

try:
    import seaborn as sns
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
except ImportError:
    sns = None
    Axes = None
    Figure = None


class DataType(CleverEnum):
    qualitative = enum.auto()
    sequential = enum.auto()
    divergent = enum.auto()


class VizResources:
    def __init__(self):
        self.override_settings = MandosResources.json_dict("viz", "style_override.json")
        self.dims = MandosResources.json_dict("viz", "page_dims.json")
        palettes = MandosResources.json_dict("viz", "palettes.json")
        self.named_palettes = palettes["named"]
        self.default_palettes = palettes["defaults"]
        self.named_cmaps = self._get_named_cmaps()

    def _get_named_cmaps(self) -> Mapping[str, Colormap]:
        cmaps = {}
        for name, cmap in self.named_palettes.items():
            cmap = NestedDotDict(cmap)
            seq = cmap.req_list_as("sequence", str)
            seq = [to_hex(c) for c in seq]
            cat = cmap.req_as("categorical", bool)
            if cat:
                cmaps[name] = ListedColormap(seq)
            else:
                nan, under, over = cmap.get("nan"), cmap.get("under"), cmap.get("over")
                cmap = LinearSegmentedColormap.from_list(name, seq)
                cmap.set_extremes(bad=nan, under=under, over=over)
        return cmaps


VIZ_RESOURCES = VizResources()


class MandosPlotStyling:
    @classmethod
    def list_named_palettes(cls) -> Set[str]:
        return {
            *VIZ_RESOURCES.named_palettes.keys(),
            *SEABORN_PALETTES,
            *plt.colormaps(),
        }

    @classmethod
    def choose_palette(
        cls,
        data: pd.DataFrame,
        col: Optional[str],
        palette: Optional[str],
    ) -> Union[None, Colormap, Mapping[str, str]]:
        if col is None:
            return None
        unique = data[col].unique()
        dtype = cls.guess_data_type(data)
        if palette is None:
            palette = cls.get_palette(None, dtype)
        if dtype is DataType.qualitative:
            if not isinstance(palette, ListedColormap):
                raise LookupFailedError(f"{palette} is not a valid choice for {dtype}")
            if len(unique) > len(palette.colors):
                raise LengthError(
                    f"Palette (N={len(palette.colors)}) too small for {len(unique)} items"
                )
            return {i: j for i, j in CommonTools.zip_strict(unique, map(to_hex, palette.colors))}
        return palette

    @classmethod
    def get_palette(cls, name: Optional[str], data_type: Union[DataType, str]) -> Colormap:
        data_type = DataType.of(data_type)
        if name is None:
            name = VIZ_RESOURCES.default_palettes[data_type.name]
        if name in VIZ_RESOURCES.named_cmaps:
            return VIZ_RESOURCES.named_cmaps[name]
        return sns.color_palette(name, as_cmap=True)

    @classmethod
    def guess_data_type(cls, data: Sequence[Union[str, float]]) -> DataType:
        numerical = cls._to_numerical(data)
        if numerical is None:
            return DataType.qualitative
        is_divergent = cls._are_floats_divergent(data)
        if is_divergent:
            return DataType.divergent
        return DataType.sequential

    @classmethod
    def _to_colors(cls, data: Sequence[Union[float, str]]) -> Optional[Sequence[str]]:
        if not all((isinstance(d, str)) for d in data):
            return None
        try:
            return [to_hex(c) for c in data]
        except ValueError:
            return None

    @classmethod
    def _to_numerical(cls, data: Sequence[Union[str, float]]) -> Optional[Sequence[float]]:
        try:
            [float(d) for d in data]
        except ValueError:
            return None

    @classmethod
    def _are_floats_divergent(cls, data: Sequence[float]):
        signs = {np.sign(d) for d in data if d != 0 and not np.isnan(d) and not np.isinf(d)}
        return len(signs) == 2

    @classmethod
    def context(
        cls, style: Union[None, str, Path], kwargs: Optional[Mapping[str, Any]]
    ) -> Generator[None, None, None]:
        """
        Override these from the default style.
        This will be called once, at startup.
        """
        new_kwargs = dict(VIZ_RESOURCES.override_settings["allow_change"])
        if kwargs is not None:
            new_kwargs.update(kwargs)
        with plt.rc_context(new_kwargs, style):
            yield

    @classmethod
    def fig_width_and_height(cls, size: str) -> Tuple[float, float]:
        if size is None:
            return plt.rcParams["figure.figsize"]
        axis_to_str = {
            i: d.strip() for i, d in enumerate(size.replace(" × ", " by ").split(" by "))
        }
        try:
            default_inch = plt.rcParams["figure.figsize"]
            width = cls._to_inch(axis_to_str.get(0), VIZ_RESOURCES.dims["widths"], default_inch[0])
            height = cls._to_inch(
                axis_to_str.get(1), VIZ_RESOURCES.dims["heights"], default_inch[1]
            )
        except ValueError:
            raise BadCommandError(f"Strange --size format in '{size}'") from None
        return width, height

    @classmethod
    def _to_inch(
        cls, s: Optional[str], standards: Mapping[str, float], default_inch: float
    ) -> float:
        if s is None or len(s) == "":
            return default_inch
        try:
            return float(s)
        except ValueError:
            pass
        x = standards.get(s, s)
        return UnitTools.canonicalize_quantity(x, "[length]").to("inch").magnitude


class MandosPlotUtils:
    @classmethod
    def save(cls, figure: Figure, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(str(path))
        figure.clear()


CompoundStyleDf = (
    TypedDfs.typed("CompoundStyleDf").require("inchikey", dtype=str).strict(cols=False).secure()
).build()

PredicateObjectStyleDf = (
    TypedDfs.typed("PredicateObjectStyleDf")
    .require("predicate", "object", dtype=str)
    .strict(cols=False)
    .secure()
).build()

PhiPsiStyleDf = (
    TypedDfs.typed("PhiPsiStyleDf").require("phi", "psi", dtype=str).strict(cols=False).secure()
).build()


__all__ = [
    "sns",
    "plt",
    "Figure",
    "Axes",
    "MandosPlotStyling",
    "MandosPlotUtils",
    "CompoundStyleDf",
    "PredicateObjectStyleDf",
    "VIZ_RESOURCES",
]
