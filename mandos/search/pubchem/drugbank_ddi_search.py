import re
from dataclasses import dataclass
from typing import Sequence, Optional

from loguru import logger

from mandos.search.pubchem import PubchemHit, PubchemSearch


@dataclass(frozen=True, order=True, repr=True)
class DrugbankDdiHit(PubchemHit):
    """ """

    type: str
    effect_target: Optional[str]
    change: Optional[str]
    description: str


class DrugbankDdiSearch(PubchemSearch[DrugbankDdiHit]):
    """ """

    @property
    def data_source(self) -> str:
        return "DrugBank :: drug/drug interactions"

    def find(self, inchikey: str) -> Sequence[DrugbankDdiHit]:
        data = self.api.fetch_data(inchikey)
        hits = []
        for dd in data.biomolecular_interactions_and_pathways.drugbank_ddis:
            kind = self._guess_type(dd.description)
            up_or_down = self._guess_up_down(dd.description)
            spec = None
            predicate = None
            if kind == "risk":
                spec = self._guess_adverse(dd.description)
                predicate = f"{kind} :: {up_or_down} risk of {spec} with"
            elif kind == "activity":
                spec = self._guess_activity(dd.description)
                predicate = f"{kind} :: {up_or_down} {spec} activity with"
            elif kind == "PK":
                spec = self._guess_pk(dd.description)
                predicate = f"{kind} :: {up_or_down} {spec} with"
            elif kind == "efficacy":
                spec = self._guess_efficacy(dd.description)
                predicate = f"{kind} :: {up_or_down} efficacy of {spec} with"
            if predicate is None:
                logger.info(f"Did not extract info from '{dd.description}'")
                continue
            hits.append(
                DrugbankDdiHit(
                    record_id=None,
                    origin_inchikey=inchikey,
                    matched_inchikey=data.names_and_identifiers.inchikey,
                    compound_id=str(data.cid),
                    compound_name=data.name,
                    predicate=predicate,
                    object_id=dd.drug_drugbank_id,
                    object_name=dd.drug_drugbank_id,
                    search_key=self.key,
                    search_class=self.search_class,
                    data_source=self.data_source,
                    type=kind,
                    effect_target=spec,
                    change=up_or_down,
                    description=dd.description,
                )
            )
        return hits

    def _guess_up_down(self, desc: str) -> str:
        if "increase" in desc:
            return "increases"
        elif "decrease" in desc:
            return "decreases"
        return "changes"

    def _guess_efficacy(self, desc: str) -> Optional[str]:
        match = re.compile("efficacy of (.+)").search(desc)
        if match is None or match.group(1) is None:
            return None
        split = match.group(1).split(" can")
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_activity(self, desc: str) -> Optional[str]:
        match = re.compile("may increase the (.+)").search(desc)
        if match is None or match.group(1) is None:
            match = re.compile("may decrease the (.+)").search(desc)
        if match is None or match.group(1) is None:
            return None
        split = re.compile("activities").split(match.group(1))
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_adverse(self, desc: str) -> Optional[str]:
        match = re.compile(" risk or severity of (.+)").search(desc)
        if match is None or match.group(1) is None:
            match = re.compile(" risk of (.+)").search(desc)
            if match is None or match.group(1) is None:
                return None
        split = re.compile(" (?:can)|(?:may) be").split(match.group(1))
        if len(split) != 2:
            return None
        return split[0].strip()

    def _guess_pk(self, desc: str) -> Optional[str]:
        match = re.compile("^The (.+)").search(desc)
        if match is not None and match.group(1) is not None:
            split = re.compile("can be").split(match.group(1))
            if len(split) == 2:
                return split[0].strip()
        # try another way
        match = re.compile("may increase the (.+)").search(desc)
        if match is None or match.group(1) is None:
            match = re.compile("may decrease the (.+)").search(desc)
        if match is None or match.group(1) is None:
            return None
        split = re.compile("which").split(match.group(1))
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


__all__ = ["DrugbankDdiHit", "DrugbankDdiSearch"]
