from typing import List, Dict, Set
from src.models.data_classes import TableMetadata


class QueryBuilder:
    def __init__(self, schema_metadata: Dict[str, TableMetadata]):
        self.schema = schema_metadata
        self.graph = self._build_relations_graph()

    def _build_relations_graph(self) -> Dict[str, Dict[str, tuple]]:
        graph = {t_name: {} for t_name in self.schema}
        for t_name, t_meta in self.schema.items():
            for field in t_meta.fields:
                if field.is_fk and field.fk_info:
                    fk = field.fk_info
                    graph[t_name][fk.to_table] = (field.name, fk.to_field)
                    if fk.to_table in graph:
                        graph[fk.to_table][t_name] = (fk.to_field, field.name)
        return graph

    def find_join_path(self, start_table: str, target_tables: Set[str]) -> List[tuple]:
        if not target_tables or start_table not in self.schema:
            return []
        visited = {start_table}
        queue = [[start_table, []]]
        needed_targets = target_tables - {start_table}
        if not needed_targets:
            return []

        while queue:
            current, path = queue.pop(0)
            for neighbor, keys in self.graph.get(current, {}).items():
                if neighbor not in visited:
                    visited.add(neighbor)
                    new_step = (current, neighbor, keys[0], keys[1])
                    new_path = path + [new_step]
                    if neighbor in needed_targets:
                        return new_path
                    queue.append([neighbor, new_path])
        return []

    def build_complex_select(self, selected_fields: dict[str, list[str]],
                             filters: list[str] = None,
                             sort_fields: list[str] = None,
                             limit: str = None) -> str:
        """
        Универсальная сборка SQL-запроса.
        Поддерживает как связанные таблицы (INNER JOIN), так и бесконечное количество
        абсолютно несвязанных таблиц (CROSS JOIN / перечисление в FROM).
        """
        if not selected_fields:
            return ""

        select_parts = []
        for t_name, fields in selected_fields.items():
            for f_name in fields:
                select_parts.append(f"{t_name}.{f_name}")

        sql = f"SELECT {', '.join(select_parts)}"

        tables_list = list(selected_fields.keys())
        base_table = tables_list[0]

        from_tables = [base_table]
        join_clauses = []
        joined_tables = {base_table}

        for target_table in tables_list[1:]:
            if target_table in joined_tables:
                continue

            path = self.find_join_path(base_table, {target_table})

            if path:
                for step in path:
                    curr_t, next_t, keys_from, keys_to = step
                    f_from, f_to = keys_from, keys_to
                    if next_t not in joined_tables:
                        join_clauses.append(f"INNER JOIN {next_t} ON {curr_t}.{f_from} = {next_t}.{f_to}")
                        joined_tables.add(next_t)
            else:
                from_tables.append(target_table)
                joined_tables.add(target_table)

        sql += f"\nFROM {', '.join(from_tables)}"

        if join_clauses:
            sql += "\n" + "\n".join(join_clauses)

        if filters:
            sql += f"\nWHERE {' AND '.join(filters)}"

        if sort_fields:
            sql += f"\nORDER BY {', '.join(sort_fields)}"

        if limit and limit.isdigit():
            sql += f"\nLIMIT {limit}"

        return sql + ";"

