import dataclasses
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True, repr=True, order=True)
class Triple:
    """
    Compound, predicate, object.
    """

    compound_id: str
    compound_lookup: str
    compound_name: str
    predicate: str
    object_name: str
    object_id: str

    @classmethod
    def tab_header(cls) -> str:
        """

        Returns:

        """
        return "\t".join(
            [
                "compound_id",
                "compound_lookup",
                "compound_name",
                "predicate",
                "object_name",
                "object_id",
            ]
        )

    @property
    def tabs(self) -> str:
        items = [
            self.compound_lookup,
            self.compound_id,
            self.compound_name,
            self.predicate,
            self.object_name,
            self.object_id,
        ]
        return "\t".join(["-" if k is None else str(k) for k in items])

    @property
    def statement(self) -> str:
        """
        Returns a simple text statement with brackets.

        Returns:

        """
        sub = f"{self.compound_lookup} [{self.compound_id}] [{self.compound_name}]>"
        pred = f"<{self.predicate}>"
        obj = f"<{self.object_name} [{self.object_id}]>"
        return "\t".join([sub, pred, obj])


@dataclass(frozen=True, order=True, repr=True)
class AbstractHit:
    """"""

    record_id: Optional[str]
    compound_id: str
    inchikey: str
    compound_lookup: str
    compound_name: str
    object_id: str
    object_name: str

    def to_triple(self) -> Triple:
        return Triple(
            compound_lookup=self.compound_lookup,
            compound_id=self.compound_id,
            compound_name=self.compound_name,
            predicate=self.predicate,
            object_id=self.object_id,
            object_name=self.object_name,
        )

    @property
    def predicate(self) -> str:
        """

        Returns:

        """
        raise NotImplementedError()

    def __hash__(self):
        return hash(self.record_id)

    @classmethod
    def fields(cls) -> Sequence[str]:
        """

        Returns:

        """
        return [f.name for f in dataclasses.fields(cls)]


__all__ = ["AbstractHit", "Triple"]
