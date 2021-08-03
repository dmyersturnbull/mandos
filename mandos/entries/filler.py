from __future__ import annotations
import enum
from typing import Set, Mapping, Optional, Union, List, Dict

from loguru import logger
from mandos.model import CleverEnum

from mandos.entries.api_singletons import Apis
from mandos.entries.searcher import IdMatchFrame, ChemFinder
from mandos.model.apis.chembl_support.chembl_utils import ChemblUtils
from mandos.model.apis.pubchem_api import PubchemCompoundLookupError
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData


PUT_FIRST = [
    "compound_id",
    "library",
    "inchikey",
    "chembl_id",
    "pubchem_id",
    "g2p_id",
    "common_name",
]
PUT_LAST = ["inchi", "smiles" "iupac", "origin_inchikey", "origin_inchi", "origin_smiles"]


class IdType(CleverEnum):
    inchikey = enum.auto()
    chembl_id = enum.auto()
    pubchem_id = enum.auto()
    # g2p_id = enum.auto()
    common_name = enum.auto()
    iupac = enum.auto()
    inchi = enum.auto()
    smiles = enum.auto()

    @classmethod
    def parse(cls, fill: str) -> Set[IdType]:
        if fill == "@all":
            return set(IdType)
        elif fill == "@primary":
            return IdType.primary()
        else:
            return {IdType.of(s.strip().lower()) for s in fill.split(",")}

    @property
    def is_primary(self) -> bool:
        return self in self.__class__.primary()

    @classmethod
    def primary(cls) -> Set[IdType]:
        # in order from best to worst
        return {IdType.inchikey, IdType.chembl_id, IdType.pubchem_id}


class CompoundIdFiller:
    def __init__(self, wanted: Set[Union[str, IdType]] = None, replace: bool = False):
        self.wanted = [IdType.of(s) for s in wanted]
        self.replace = replace

    def fill(
        self,
        df: IdMatchFrame,
    ) -> IdMatchFrame:
        df = df.copy()
        df = df.dropna(how="all", axis=1)
        sources: Set[IdType] = {s for s in IdType.primary() if s.name in df.columns}
        targets: Set[IdType] = {s for s in self.wanted if s.name not in df.columns or self.replace}
        if len(sources) == 0:
            raise ValueError(f"No valid sources in list {df.columns.values}")
        source = next(iter(sources))
        # noinspection PyUnresolvedReferences
        logger.notice(f"Getting {', '.join([s.name for s in targets])} from {source.name}")
        # watch out! these are simply in order, nothing more
        remapped: Dict[IdType, List[str]] = {t: [] for t in IdType}
        for i, source_val in enumerate(df[source.name].values):
            if source_val is None:
                raise AssertionError()
            matches: Dict[IdType, str] = self._matches(source, source_val, targets)
            for target, target_val in matches.items():
                remapped[target].append(target_val)
            logger.info(f"Processed {source_val} ({i} of {len(df)}")
            if i % 20 == 0 and i > 0:
                logger.notice(f"Processed {i} / {len(df)}")
        for target in targets:
            rx = remapped[target]
            df[target.name] = rx
        order = [o for o in PUT_FIRST if o in df.columns]
        order += [c for c in df.columns if c not in PUT_FIRST and c not in PUT_LAST]
        order += [o for o in PUT_LAST if o in df.columns]
        df = df.cfirst(order)
        return df

    def _matches(self, source: IdType, source_val: str, targets: Set[IdType]) -> Dict[IdType, str]:
        if source is IdType.pubchem_id:
            inchikey = Apis.Pubchem.find_inchikey(int(source_val))
        elif source is IdType.chembl_id:
            # TODO
            # get_compound wants an inchikey,
            # but we're secretly passing a CHEMBLxxxx ID instead
            # we just know that that works
            inchikey = ChemblUtils(Apis.Chembl).get_compound(source_val).inchikey
        elif source is IdType.inchikey:
            inchikey = source
        else:
            raise AssertionError(source.name)
        matched: Dict[IdType, str] = {k: None for k in self.wanted}
        matched[IdType.inchikey] = inchikey
        if IdType.pubchem_id in targets:
            try:
                pubchem_data: Optional[PubchemData] = Apis.Pubchem.fetch_data(inchikey)
            except PubchemCompoundLookupError:
                pubchem_data = None
            if pubchem_data is not None:
                matched[IdType.pubchem_id] = str(pubchem_data.cid)
                if IdType.common_name in targets:
                    matched[IdType.common_name] = pubchem_data.name
                if IdType.iupac in targets:
                    matched[IdType.iupac] = pubchem_data.names_and_identifiers.iupac
                if IdType.smiles in targets:
                    matched[IdType.smiles] = pubchem_data.names_and_identifiers.isomeric_smiles
                if IdType.inchi in targets:
                    matched[IdType.inchi] = pubchem_data.names_and_identifiers.inchi
        if IdType.chembl_id in targets:
            chembl_id = ChemFinder.chembl().find(inchikey)
            if chembl_id is not None:
                matched[IdType.chembl_id] = chembl_id
        return matched


__all__ = ["IdType", "CompoundIdFiller"]
