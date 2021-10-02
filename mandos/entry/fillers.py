from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping, Optional, Tuple

from pocketutils.core.exceptions import XValueError
from pocketutils.tools.common_tools import CommonTools
from typeddfs import TypedDfs

from mandos.entry.api_singletons import Apis
from mandos.model import CompoundNotFoundError, CompoundStruct
from mandos.model.apis.chembl_support.chembl_utils import ChemblUtils
from mandos.model.apis.pubchem_support.pubchem_data import PubchemData
from mandos.model.utils.setup import logger


IdMatchDf = (
    TypedDfs.typed("IdMatchDf")
    .reserve("inchikey", dtype=str)
    .reserve("compound_id", "compound_name", "library", dtype=str)
    .reserve("inchi", dtype=str)
    .reserve("chembl_id", "pubchem_id", "hmdb_id", dtype=str)
    .reserve("chembl_inchikey", "pubchem_inchikey", dtype=str)
    .reserve("chembl_inchi", "pubchem_inchi", dtype=str)
    .reserve("origin_inchi", "origin_inchikey", dtype=str)
    .strict(cols=False)
    .secure()
    .hash(file=True)
).build()


FILL_IDS = [
    "inchi",
    "inchikey",
    "chembl_id",
    "pubchem_id",
    "chembl_inchi",
    "chembl_inchikey",
    "pubchem_inchi",
    "pubchem_inchikey",
]
PUT_FIRST = [
    "compound_id",
    "compound_name",
    "library",
    "inchikey",
    "chembl_id",
    "pubchem_id",
    "g2p_id",
    "chembl_inchikey",
    "pubchem_inchikey",
    "origin_inchikey",
]
PUT_LAST = ["inchi", "chembl_inchi", "pubchem_inchi", "origin_inchi", "smiles"]

Db = str


def look(obj, attrs):
    s = CommonTools.look(obj, attrs)
    if isinstance(s, str) and s.upper() == "N/A":
        return None
    return None if CommonTools.is_probable_null(s) else s


@dataclass(frozen=True, repr=True)
class CompoundIdFiller:
    chembl: bool = True
    pubchem: bool = True

    def fill(self, df: IdMatchDf) -> IdMatchDf:
        df = self._prep(df)
        logger.info(f"Processing {len(df)} input compounds")
        fill = []
        for i, row in enumerate(df.itertuples()):
            if i % 200 == 0 and i > 0:
                logger.notice(f"Processed {i:,} / {len(df):,}")
            elif i % 20 == 0 and i > 0:
                logger.info(f"Processed {i:,} / {len(df):,}")
            with logger.contextualize(line=i):
                proc = self._process(
                    compound_id=look(row, "compound_id"),
                    library=look(row, "library"),
                    inchi=look(row, "origin_inchi"),
                    inchikey=look(row, "origin_inchikey"),
                    pubchem_id=look(row, "origin_pubchem_id"),
                    chembl_id=look(row, "origin_chembl_id"),
                )
            fill.append(proc)
        for c in FILL_IDS:
            df[c] = [r[c] for r in fill]
        duplicate_cols = []
        for c in FILL_IDS:
            if c in df.columns and "origin_" + c in df.columns:
                if df[c].values.tolist() == df["origin_" + c].values.tolist():
                    duplicate_cols.append("origin_" + c)
        logger.notice(f"Done — filled {len(df):,} rows")
        if len(duplicate_cols) > 0:
            df = df.drop_cols(duplicate_cols)
            logger.notice(f"Dropped duplicated columns {', '.join(duplicate_cols)}")
        order = [o for o in PUT_FIRST if o in df.columns]
        order += [c for c in df.columns if c not in PUT_FIRST and c not in PUT_LAST]
        order += [o for o in PUT_LAST if o in df.columns]
        df = df.cfirst(order)
        have_chembl = len(df) - len(df[df["chembl_id"].isnull()]["chembl_id"].tolist())
        have_pubchem = len(df) - len(df[df["pubchem_id"].isnull()]["pubchem_id"].tolist())
        logger.notice(f"{have_chembl:,}/{len(df):,} have ChEMBL IDs")
        logger.notice(f"{have_pubchem:,}/{len(df):,} have PubChem IDs")
        return df

    def _process(
        self,
        compound_id: Optional[str],
        library: Optional[str],
        inchi: Optional[str],
        inchikey: Optional[str],
        pubchem_id: Optional[str],
        chembl_id: Optional[str],
    ) -> Mapping[str, Any]:
        if inchikey is pubchem_id is chembl_id is None:
            logger.error(f"[line {line_no}] No data for {compound_id}")
            return dict(
                inchi=inchi,
                inchikey=inchikey,
                chembl_id=None,
                chembl_inchi=None,
                chembl_inchikey=None,
                pubchem_id=None,
                pubchem_inchi=None,
                pubchem_inchikey=None,
            )
        fake_x = CompoundStruct("input", compound_id, inchi, inchikey)
        chembl_x = self._get_chembl(inchikey, chembl_id)
        pubchem_x = self._get_pubchem(inchikey, pubchem_id)
        #################################################################################
        # This is important and weird!
        # Where DNE = does not exist and E = exists
        # If chembl DNE and pubchem E ==> fill chembl
        # THEN: If chembl E and (pubchem E or pubchem DNE) ==> fill pubchem
        # we might therefore go from pubchem --> chembl --> pubchem
        # The advantage is that chembl might have a good parent compound
        # Whereas pubchem does not
        # This is often true: chembl is much better at this than pubchem
        # In contrast, only fill ChEMBL if it's missing
        if chembl_x is None and pubchem_x is not None:
            chembl_x = self._get_chembl(pubchem_x.inchikey, None)
        if chembl_x is not None:
            pubchem_x = self._get_pubchem(chembl_x.inchikey, None)
        #################################################################################
        # the order is from best to worst
        prioritize_choices = [chembl_x, pubchem_x, fake_x]
        db_to_struct = {o.db: o for o in prioritize_choices if o is not None}
        inchikey, inchikey_choices = self._choose(db_to_struct, "inchikey")
        inchi, inchi_choices = self._choose(db_to_struct, "inchi")
        about = " ; ".join([x.simple_str for x in prioritize_choices if x is not None])
        if len(inchikey_choices) == 0:
            logger.error(f"[line {line_no}] no database inchikeys found :: {about}")
        elif len(inchikey_choices) > 1:
            logger.error(f"[line {line_no}] inchikey mismatch :: {about} :: {inchikey_choices}")
        elif len(inchi_choices) > 1:
            logger.debug(f"[line {line_no}] inchi mismatch :: {about} :: {inchi_choices}")
        return dict(
            inchi=inchi,
            inchikey=inchikey,
            chembl_id=look(chembl_x, "id"),
            chembl_inchi=look(chembl_x, "inchi"),
            chembl_inchikey=look(chembl_x, "inchikey"),
            pubchem_id=look(pubchem_x, "id"),
            pubchem_inchi=look(pubchem_x, "inchi"),
            pubchem_inchikey=look(pubchem_x, "inchikey"),
        )

    def _choose(
        self,
        db_to_struct: Mapping[str, CompoundStruct],
        what: str,
    ) -> Tuple[Optional[str], MutableMapping[str, Db]]:
        """
        Chooses the best what="inchi" or what="inchikey".

        Arguments:
            db_to_struct: Should be in order from most preferred to least
            what: The name of the CompoundStruct attribute to access
        """
        options = {o.db: look(o, what) for o in db_to_struct.values() if look(o, what) is not None}
        _s = ", ".join([f"{k}={v}" for k, v in options.items()])
        non_input_dbs = {v: k for k, v in options.items() if k != "input"}
        all_uniques = set(options.values())
        if len(all_uniques) == 0:
            return None, {}
        else:
            return list(all_uniques)[0], non_input_dbs

    def _prep(self, df: IdMatchDf) -> IdMatchDf:
        bad_cols = [c for c in df.columns if c.startswith("origin_")]
        if len(bad_cols) > 0:
            raise XValueError(f"Columns {', '.join(bad_cols)} start with 'origin_'")
        rename_cols = {c: "origin_" + c for c in FILL_IDS if c in df.columns}
        if len(rename_cols) > 0:
            logger.notice(f"Renaming columns: {', '.join(rename_cols.keys())}")
        df: IdMatchDf = df.rename(columns=rename_cols)
        drop_cols = {c for c in df.columns if df[c].isnull().all()}
        if len(drop_cols):
            logger.warning(f"Dropping empty columns: {', '.join(drop_cols)}")
        df = df.drop_cols(drop_cols)
        return df

    def _get_pubchem(self, inchikey: Optional[str], cid: Optional[int]) -> Optional[CompoundStruct]:
        api = Apis.Pubchem
        if cid is not None:
            # let it raise a CompoundNotFoundError
            inchikey = api.fetch_data(int(cid)).names_and_identifiers.inchikey
            if inchikey is None:
                return None
        if inchikey is not None:
            try:
                data: Optional[PubchemData] = api.fetch_data(inchikey)
            except CompoundNotFoundError:
                return None
            return None if data is None else data.struct_view

    def _get_chembl(self, inchikey: Optional[str], cid: Optional[str]) -> Optional[CompoundStruct]:
        util = ChemblUtils(Apis.Chembl)
        if cid is not None:
            # let it raise a CompoundNotFoundError
            return util.get_compound(cid).struct_view
        try:
            return util.get_compound(inchikey).struct_view
        except CompoundNotFoundError:
            return None


__all__ = ["CompoundIdFiller", "IdMatchDf"]
