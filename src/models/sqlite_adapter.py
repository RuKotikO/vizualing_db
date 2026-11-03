import sqlite3
import hashlib
from src.models.base_connector import DatabaseConnector
from src.models.data_classes import TableMetadata, FieldMetadata, ForeignKeyRelation


class SQLiteAdapter(DatabaseConnector):
    """Адаптер для работы с базами данных формата SQLite."""
    def __init__(self, db_path: str = "app_internal.db"):
        """Инициализирует экземпляр адаптера SQLite."""
        self.db_path = db_path
        self.conn = None

    def connect(self, **kwargs) -> bool:
        """
        Устанавливает соединение с файлом базы данных.
        Если в kwargs передан ключ 'db_path', подключается к нему.
        """
        target_path = kwargs.get("db_path", self.db_path)
        try:
            self.conn = sqlite3.connect(target_path)
            self.conn.execute("PRAGMA foreign_keys = ON;")
            self._init_internal_tables()
            return True
        except sqlite3.Error as e:
            raise e

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, sql_text: str, params: tuple = ()) -> list[tuple]:
        if not self.conn:
            raise ConnectionError("БД не подключена.")
        cursor = self.conn.cursor()
        cursor.execute(sql_text, params)
        if sql_text.strip().upper().startswith("SELECT"):
            return cursor.fetchall()
        self.conn.commit()
        return []

    def get_schema_metadata(self) -> dict[str, TableMetadata]:
        """
        Логика интроспекции структуры любого локального файла .db.
        Считывает метаданные таблиц, типы столбцов и ограничения FOREIGN KEY.
        """
        if not self.conn:
            raise ConnectionError("Невозможно собрать метаданные: соединение отсутствует.")

        schema_dict: dict[str, TableMetadata] = {}
        cursor = self.conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables_raw = cursor.fetchall()

        tables = [row[0] for row in tables_raw]

        for table_name in tables:
            schema_dict[table_name] = TableMetadata(name=table_name)

            cursor.execute(f"PRAGMA table_info({table_name});")
            columns_info = cursor.fetchall()

            for col in columns_info:
                col_name = col[1]
                col_type = col[2].upper() if col[2] else "TEXT"
                is_pk = bool(col[5])

                field_meta = FieldMetadata(name=col_name, data_type=col_type, is_pk=is_pk)
                schema_dict[table_name].fields.append(field_meta)

            cursor.execute(f"PRAGMA foreign_key_list({table_name});")
            fk_info_list = cursor.fetchall()

            for fk in fk_info_list:
                to_table = fk[2]
                from_field = fk[3]
                to_field = fk[4]

                for f in schema_dict[table_name].fields:
                    if f.name == from_field:
                        f.is_fk = True
                        f.fk_info = ForeignKeyRelation(
                            from_field=from_field,
                            to_table=to_table,
                            to_field=to_field
                        )

        return schema_dict

    def update_connection_profile(self, old_title: str, title: str, db_type: str, host: str, port: int, db_name: str,
                                  db_user: str) -> bool:
        """Обновляет существующий профиль подключения (UPDATE) по его старому названию."""
        try:
            self.execute_query(
                """UPDATE connections 
                   SET title = ?, db_type = ?, host = ?, port = ?, db_name = ?, db_user = ? 
                   WHERE title = ?;""",
                (title, db_type, host, port, db_name, db_user, old_title)
            )
            return True
        except sqlite3.Error:
            return False

    def _init_internal_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                last_login TEXT
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                db_type TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                db_name TEXT NOT NULL,
                db_user TEXT NOT NULL,
                save_password INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
        """)
        self.conn.commit()

    def is_user_exists(self, username: str) -> bool:
        """"Проверяет учетные данные пользователя в служебной базе данных."""
        result = self.execute_query(
            "SELECT id FROM users WHERE user_name = ? LIMIT 1;",
            (username,)
        )
        return len(result) > 0

    def register_user(self, username: str, password: str) -> bool:
        try:
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()
            self.execute_query(
                "INSERT INTO users (user_name, password_hash) VALUES (?, ?);",
                (username, pwd_hash)
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate_user(self, username: str, password: str) -> bool:
        """Проверяет учетные данные пользователя в служебной базе данных."""
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        result = self.execute_query(
            "SELECT id FROM users WHERE user_name = ? AND password_hash = ?;",
            (username, pwd_hash)
        )
        return len(result) > 0

    def save_connection_profile(self, title: str, user_id: int, db_type: str, host: str, port: int, db_name: str,
                                db_user: str) -> bool:
        try:
            self.execute_query(
                """INSERT INTO connections (title, user_id, db_type, host, port, db_name, db_user) 
                   VALUES (?, ?, ?, ?, ?, ?, ?);""",
                (title, user_id, db_type, host, port, db_name, db_user)
            )
            return True
        except sqlite3.Error:
            return False

    def get_connection_profiles(self, user_id: int) -> list[tuple]:
        """Загружает сохраненные профили сетевых и локальных подключений."""
        return self.execute_query(
            "SELECT id, title, host, port, db_name FROM connections WHERE user_id = ?;",
            (user_id,)
        )

    def log_message(self, level: str, message: str):
        self.execute_query(
            "INSERT INTO system_logs (log_level, message) VALUES (?, ?);",
            (level, message)
        )

    def delete_connection_profile(self, title: str) -> bool:
        """Удаляет профиль подключения из локальной базы данных."""
        try:
            self.execute_query("DELETE FROM connections WHERE title = ?;", (title,))
            if self.conn:
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            self.log_message("ERROR", f"Не удалось удалить профиль {title}: {e}")
            return False

