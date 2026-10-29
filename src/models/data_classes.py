from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ForeignKeyRelation:
    from_field: str
    to_table: str
    to_field: str

@dataclass
class FieldMetadata:
    name: str
    data_type: str
    is_pk: bool = False
    is_fk: bool = False
    fk_info: Optional[ForeignKeyRelation] = None

@dataclass
class TableMetadata:
    name: str
    fields: List[FieldMetadata] = field(default_factory=list)

    def get_pk_fields(self) -> List[str]:
        return [f.name for f in self.fields if f.is_pk]

    def get_fk_relations(self) -> List[ForeignKeyRelation]:
        return [f.fk_info for f in self.fields if f.is_fk and f.fk_info is not None]
