from abc import ABC, abstractmethod
from typing import List, Dict
from src.models.data_classes import TableMetadata

class DatabaseConnector(ABC):
    @abstractmethod
    def connect(self, **kwargs) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_schema_metadata(self) -> Dict[str, TableMetadata]:
        pass

    @abstractmethod
    def execute_query(self, sql_text: str, params: tuple = ()) -> List[tuple]:
        pass
