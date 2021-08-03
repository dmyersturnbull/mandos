import abc
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Type

import numpy as np
import orjson
import pandas as pd
from pocketutils.tools.common_tools import CommonTools
from typeddfs import TypedDf, TypedDfs

from mandos.model import Api, CompoundNotFoundError, MANDOS_SETTINGS
from mandos.model.apis.g2p_data import G2pData, G2pInteraction, TrueFalseUnknown

LIGANDS_URL = "https://www.guidetopharmacology.org/DATA/ligand_id_mapping.tsv"
INTERACTIONS_URL = "https://www.guidetopharmacology.org/DATA/interactions.tsv"
_DEF_SUFFIX = MANDOS_SETTINGS.archive_filename_suffix


def _oint(x: str) -> Optional[int]:
    if x is None or isinstance(x, str) and x.strip() == "":
        return None
    return int(x)


LigandDf = (
    TypedDfs.typed("LigandDf")
    .require("Ligand id", dtype=int)
    .require("Name", "Type", "Approved", "PubChem CID", "InChIKey", dtype=str)
).build()


InteractionDf = (
    TypedDfs.typed("InteractionDf")
    .require("target", "target_id", dtype=str)
    .require("target_gene_symbol", "target_uniprot", dtype=str)
    .require("target_species", dtype=str)
    .require("ligand", dtype=str)
    .require("ligand_id", dtype=int)
    .require("type", "action", dtype=str)
    .require("selectivity", "endogenous", "primary_target", dtype=str)
    .require("affinity_units", dtype=str)
    .require("affinity_median", dtype=np.float64)
).build()


class G2pApi(Api, metaclass=abc.ABCMeta):
    def fetch(self, inchikey: str) -> G2pData:
        raise NotImplementedError()


class CachedG2pApi(G2pApi, metaclass=abc.ABCMeta):
    def __init__(self, cache_path: Path):
        self.cache_path = Path(cache_path)
        self.ligands: LigandDf = None
        self.interactions: InteractionDf = None

    def fetch(self, inchikey: str) -> G2pData:
        """ """
        series = self.ligands[self.ligands["inchikey"] == inchikey]
        if len(series) == 0:
            raise CompoundNotFoundError(f"G2P ligand {inchikey} not found")
        basic = dict(CommonTools.only(series).to_dict())
        g2pid = int(basic["Ligand id"])
        interactions = [
            self._convert_interaction(series)
            for series in self.interactions[self.interactions["ligand_id"] == g2pid]
        ]
        return G2pData(
            inchikey=basic["InChIKey"],
            g2pid=g2pid,
            name=basic["ligand"],
            type=basic["Type"],
            approved=TrueFalseUnknown.parse(basic["Approved"]),
            pubchem_id=_oint(basic["PubChem ID"]),
            interactions=interactions,
        )

    def download(self, force: bool = False) -> None:
        if self.ligands is None or self.interactions is None or force:
            # always download both together -- we don't want them non-synced
            if self.ligands_path.exists() and self.interactions_path.exists() and not force:
                self.ligands = LigandDf.read_file(self.ligands_path)
                self.interactions = InteractionDf.read_file(self.ligands_path)
            else:
                self.ligands = LigandDf.read_file(LIGANDS_URL, sep="\t")
                self.ligands.write_file(self.ligands_path)
                self.interactions = InteractionDf.read_file(INTERACTIONS_URL, sep="\t")
                self.interactions.write_file(self.interactions_path)
                info = dict(dt_downloaded=datetime.now().isoformat())
                info = orjson.dumps(info).decode(encoding="utf8")
                (self.cache_path / "info.json").write_text(info)

    @property
    def ligands_path(self) -> Path:
        return (self.cache_path / "ligands").with_suffix(_DEF_SUFFIX)

    @property
    def interactions_path(self) -> Path:
        return (self.cache_path / "interactions").with_suffix(_DEF_SUFFIX)

    def _load_file(self, clazz: Type[TypedDf], path: Path, url: str) -> pd.DataFrame:
        if path.exists():
            return clazz.read_file(self.ligands_path)
        else:
            df = clazz.read_file(url)
            df.write_file(self.ligands_path)
            return df

    def _convert_interaction(self, series: pd.Series) -> G2pInteraction:
        d = dict(series.to_dict())
        sel_map = {
            "Selective": TrueFalseUnknown.true,
            "Non-selective": TrueFalseUnknown.false,
            "Not Determined": TrueFalseUnknown.unknown,
        }
        d["selectivity"] = sel_map.get(d["selectivity"], TrueFalseUnknown.unknown)
        d["primary_target"] = TrueFalseUnknown.parse(d["primary_target"])
        d["endogenous"] = TrueFalseUnknown.parse(d["endogenous"])
        return G2pInteraction(**d)

    def __repr__(self):
        loaded = "not loaded" if self.ligands is None else f"n={len(self.ligands)}"
        return f"{self.__class__.__name__}({self.cache_path} : {loaded})"

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        raise NotImplementedError(f"Cannot compare {self.__class__.__name__}")


_all__ = ["G2pApi", "CachedG2pApi"]
