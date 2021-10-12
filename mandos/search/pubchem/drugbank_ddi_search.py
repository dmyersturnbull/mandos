from typing import Optional, Sequence

import regex

from mandos import logger
from mandos.model.apis.pubchem_support.pubchem_models import DrugbankDdi
from mandos.model.concrete_hits import DrugbankDdiHit
from mandos.search.pubchem import PubchemSearch


def _re(s: str) -> regex.Pattern:
    return regex.compile(s, flags=regex.V1)


class DrugbankDdiSearch(PubchemSearch[DrugbankDdiHit]):
    """ """

    def find(self, inchikey: str) -> Sequence[DrugbankDdiHit]:
        data = self.api.fetch_data(inchikey)
        hits = []
        for dd in data.biomolecular_interactions_and_pathways.drugbank_ddis:
            kind = self._guess_type(dd.description)
            direction = self._guess_direction(dd.description)
            spec = self._guess_spec(dd, kind)
            source = self._format_source(kind=kind, spec=spec)
            predicate = self._format_predicate(kind=kind, spec=spec, direction=direction)
            hits.append(
                self._create_hit(
                    inchikey=inchikey,
                    c_id=str(data.cid),
                    c_origin=inchikey,
                    c_matched=data.names_and_identifiers.inchikey,
                    c_name=data.name,
                    data_source=source,
                    predicate=predicate,
                    object_id=dd.drug_drugbank_id,
                    object_name=dd.drug_drugbank_id,
                    type=kind,
                    effect_target=spec,
                    change=direction,
                    description=dd.description,
                )
            )
        return hits

    def _guess_spec(self, dd: DrugbankDdi, kind: str) -> Optional[str]:
        if kind == "risk":
            return self._guess_adverse(dd.description)
        elif kind == "activity":
            return self._guess_activity(dd.description)
        elif kind == "PK":
            return self._guess_pk(dd.description)
        elif kind == "efficacy":
            return self._guess_efficacy(dd.description)
        else:
            logger.debug(f"Did not extract info from '{dd.description}'")
        return None

    def _guess_direction(self, desc: str) -> str:
        if "increase" in desc:
            return "up"
        elif "decrease" in desc:
            return "down"
        return "neutral"

    def _guess_efficacy(self, desc: str) -> Optional[str]:
        match = _re("efficacy of (.+)").search(desc)
        if match is None or match.group(1) is None:
            return None
        split = match.group(1).split(" can")
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_activity(self, desc: str) -> Optional[str]:
        match = _re("may increase the (.+)").search(desc)
        if match is None or match.group(1) is None:
            match = _re("may decrease the (.+)").search(desc)
        if match is None or match.group(1) is None:
            return None
        split = _re("activities").split(match.group(1))
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_adverse(self, desc: str) -> Optional[str]:
        match = _re(" risk or severity of (.+)").search(desc)
        if match is None or match.group(1) is None:
            match = _re(" risk of (.+)").search(desc)
            if match is None or match.group(1) is None:
                return None
        split = _re(" (?:can)|(?:may) be").split(match.group(1))
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_pk(self, desc: str) -> Optional[str]:
        match = _re("^The (.+)").search(desc)
        if match is not None and match.group(1) is not None:
            split = _re("can be").split(match.group(1))
            if len(split) == 2:
                return split[0].strip()
        # try another way
        match = _re("may increase the (.+)").search(desc)
        if match is None or match.group(1) is None:
            match = _re("may decrease the (.+)").search(desc)
        if match is None or match.group(1) is None:
            return None
        split = _re("which").split(match.group(1))
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_type(self, desc: str) -> str:
        for k, v in {
            "serum concentration": "PK",
            "metabolism": "PK",
            "absorption": "PK",
            "excretion": "PK",
            "risk": "risk",
            "severity": "risk",
            "adverse": "risk",
            "activities": "activity",
            "activity": "activity",
            "efficacy": "efficacy",
        }.items():
            if k in desc:
                return v
        return "unknown"


__all__ = ["DrugbankDdiSearch"]
