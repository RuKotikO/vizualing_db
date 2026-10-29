import psycopg2
from psycopg2 import OperationalError
from typing import List, Dict
from src.models.base_connector import DatabaseConnector
from src.models.data_classes import TableMetadata, FieldMetadata, ForeignKeyRelation


class PostgreSQLAdapter(DatabaseConnector):
    def __init__(self):
        self.conn = None

    def connect(self, **kwargs) -> bool:
        try:
            self.conn = psycopg2.connect(
                host=kwargs.get("host", "localhost"),
                port=kwargs.get("port", 5432),
                database=kwargs.get("database"),
                user=kwargs.get("user"),
                password=kwargs.get("password"),
                connect_timeout=3
            )
            return True
        except OperationalError as e:
            raise e

    def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute_query(self, sql_text: str, params: tuple = ()) -> List[tuple]:
        if not self.conn:
            raise ConnectionError("Нет сетевого соединения.")
        cursor = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql_text, params)
            if cursor.description:
                return cursor.fetchall()
            self.conn.commit()
            return []
        finally:
            if cursor is not None:
                cursor.close()

    def get_schema_metadata(self) -> Dict[str, TableMetadata]:
        if not self.conn:
            raise ConnectionError("Соединение отсутствует.")

        schema_dict: Dict[str, TableMetadata] = {}

        columns_query = """
            SELECT table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position;
        """
        for row in self.execute_query(columns_query):
            t_name, c_name, d_type = row
            if t_name not in schema_dict:
                schema_dict[t_name] = TableMetadata(name=t_name)
            schema_dict[t_name].fields.append(FieldMetadata(name=c_name, data_type=d_type.upper()))

        pk_query = """
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public';
        """
        for row in self.execute_query(pk_query):
            t_name, c_name = row
            if t_name in schema_dict:
                for f in schema_dict[t_name].fields:
                    if f.name == c_name:
                        f.is_pk = True

        fk_query = """
            SELECT kcu.table_name AS f_t, kcu.column_name AS f_c, ccu.table_name AS t_t, ccu.column_name AS t_c
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
        """
        for row in self.execute_query(fk_query):
            f_t, f_c, t_t, t_c = row
            if f_t in schema_dict:
                for f in schema_dict[f_t].fields:
                    if f.name == f_c:
                        f.is_fk = True
                        f.fk_info = ForeignKeyRelation(from_field=f_c, to_table=t_t, to_field=t_c)

        return schema_dict
