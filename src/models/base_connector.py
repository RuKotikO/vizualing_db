from abc import ABC, abstractmethod
from typing import List, Dict
from src.models.data_classes import TableMetadata

class DatabaseConnector(ABC):
    """Абстрактный базовый класс для всех адаптеров баз данных."""
    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """Устанавливает физическое соединение с сервером или файлом БД."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Безопасно разрывает текущее активное соединение с СУБД."""
        pass

    @abstractmethod
    def get_schema_metadata(self) -> Dict[str, TableMetadata]:
        """Осуществляет интроспекцию системных каталогов для извлечения схемы."""
        pass

    @abstractmethod
    def execute_query(self, sql_text: str, params: tuple = ()) -> List[tuple]:
        """Выполняет SQL-выборку и возвращает структурированный результат."""
        pass
