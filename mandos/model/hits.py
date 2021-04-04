import dataclasses
from dataclasses import dataclass
from typing import Optional, Sequence

from typeddfs import TypedDfs


@dataclass(frozen=True, repr=True, order=True)
class Triple:
    """
    Compound, predicate, object.
    """

    inchikey: str
    compound_id: str
    compound_name: str
    predicate: str
    object_name: str
    object_id: str

    @property
    def statement(self) -> str:
        """
        Returns a simple text statement.
        """
        return f'"{self.inchikey}"\t"{self.predicate}"\t"{self.object_name}"'


@dataclass(frozen=True, order=True, repr=True)
class AbstractHit:
    """
    An abstract annotation (statement type), which may support additional fields.
    """

    record_id: Optional[str]
    origin_inchikey: str
    matched_inchikey: str
    compound_id: str
    compound_name: str
    predicate: str
    object_id: str
    object_name: str
    search_key: str
    search_class: str
    data_source: str

    def to_triple(self) -> Triple:
        return Triple(
            inchikey=self.origin_inchikey,
            compound_id=self.compound_id,
            compound_name=self.compound_name,
            predicate=self.predicate,
            object_id=self.object_id,
            object_name=self.object_name,
        )

    def __hash__(self):
        return hash(self.record_id)

    @property
    def universal_id(self) -> str:
        """
        Gets an identifier (a hex key) that uniquely identifies the record by its unique attributes.
        Does **NOT** distinguish between hits with duplicate information and does **NOT**
        include ``record_id``.

        Returns:
            A 64-character hexadecimal string
        """
        # excluding record_id only because it's not available for some hit types
        # we'd rather immediately see duplicates if the exist
        fields = {
            field
            for field in self.fields()
            if field
            not in {"record_id", "origin_inchikey", "compound_name", "search_key", "search_class"}
        }
        return hex(hash(tuple([getattr(self, f) for f in fields])))

    @classmethod
    def fields(cls) -> Sequence[str]:
        """
        Finds the list of fields in this class by reflection.
        """
        return [f.name for f in dataclasses.fields(cls)]


HitFrame = (
    TypedDfs.typed("HitFrame")
    .require("record_id")
    .require("inchikey", "compound_id", "compound_name")
    .require("predicate")
    .require("object_id", "object_name")
    .require("search_key", "search_class", "data_source")
).build()


__all__ = ["AbstractHit", "Triple", "HitFrame"]
