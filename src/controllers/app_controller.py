from src.models.postgres_adapter import PostgreSQLAdapter
from src.models.sqlite_adapter import SQLiteAdapter


class AppController:
    """
    Контроллер управления сессией активной базы данных.
    Динамически переключается между файловым SQLite и сетевым PostgreSQL движками.
    """

    def __init__(self, main_window):
        self.main_window = main_window
        self.postgres_connector = PostgreSQLAdapter()
        self.sqlite_connector = SQLiteAdapter()

        self.active_connector = None
        self.active_metadata = {}

    def connect_to_database(self, db_type, **kwargs) -> bool:
        """Переключает активный движок и инициализирует сессию интроспекции."""
        try:
            if self.active_connector:
                self.active_connector.disconnect()

            if db_type == "SQLite":
                self.active_connector = self.sqlite_connector
                file_path = kwargs.get("database")
                success = self.active_connector.connect(db_path=file_path)
            else:
                self.active_connector = self.postgres_connector
                success = self.active_connector.connect(**kwargs)

            if success:
                # 1. Запускаем интроспекцию структуры выбранной базы данных
                self.active_metadata = self.active_connector.get_schema_metadata()

                # 2. Передаем метаданные И ссылку на MainWindow для корректной подписки сигналов
                self.main_window.scene.render_schema(self.active_metadata, self.main_window)
                return True
            return False
        except Exception as e:
            # Выводим реальный трейсбек ошибки в консоль, чтобы локализовать проблему, если она в коде
            import traceback
            traceback.print_exc()

            self.main_window.lbl_connection_status.setText(f"Ошибка подключения: {e}")
            return False

    def get_active_schema(self) -> dict:
        """Возвращает метаданные активной СУБД для выпадающих списков."""
        return self.active_metadata
