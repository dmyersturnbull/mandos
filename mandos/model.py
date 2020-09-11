import logging
from dataclasses import dataclass

logger = logging.getLogger("mandos")


@dataclass(frozen=True, order=True)
class AbstractHit:
    record_id: int
    compound_id: int
    compound_lookup: str
    compound_name: str

    @property
    def predicate(self) -> str:
        raise NotImplementedError()
