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
                        return new_path  # Возвращаем путь как только нашли связующую ноду
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

        # 1. Формируем секцию SELECT
        select_parts = []
        for t_name, fields in selected_fields.items():
            for f_name in fields:
                select_parts.append(f"{t_name}.{f_name}")

        sql = f"SELECT {', '.join(select_parts)}"

        # 2. Распределяем таблицы на связанные группы и изолированные ноды
        tables_list = list(selected_fields.keys())
        base_table = tables_list[0]

        # Контейнеры для сборки структуры FROM / JOIN
        from_tables = [base_table]
        join_clauses = []
        joined_tables = {base_table}

        # Проходим по всем остальным запрошенным таблицам
        for target_table in tables_list[1:]:
            if target_table in joined_tables:
                continue

            # Пытаемся найти путь в графе FOREIGN KEY связей от базовой таблицы
            path = self.find_join_path(base_table, {target_table})

            if path:
                # Если путь есть — строим цепочку INNER JOIN
                for step in path:
                    curr_t, next_t, keys_from, keys_to = step
                    # Извлекаем имена полей из кортежа связей графа
                    f_from, f_to = keys_from, keys_to
                    if next_t not in joined_tables:
                        join_clauses.append(f"INNER JOIN {next_t} ON {curr_t}.{f_from} = {next_t}.{f_to}")
                        joined_tables.add(next_t)
            else:
                # ИСПРАВЛЕНО: Если пути через FOREIGN KEY нет — таблица изолирована!
                # Добавляем её в секцию FROM как независимый источник (CROSS JOIN)
                from_tables.append(target_table)
                joined_tables.add(target_table)

        # 3. Собираем секцию FROM и JOIN воедино
        # Все несвязанные базовые таблицы перечисляются через запятую
        sql += f"\nFROM {', '.join(from_tables)}"

        # Если были какие-то связанные подграфы, дописываем их JOIN-условия
        if join_clauses:
            sql += "\n" + "\n".join(join_clauses)

        # 4. Секция WHERE (Фильтры)
        if filters:
            sql += f"\nWHERE {' AND '.join(filters)}"

        # 5. Секция ORDER BY (Сортировка)
        if sort_fields:
            sql += f"\nORDER BY {', '.join(sort_fields)}"

        # 6. Секция LIMIT
        if limit and limit.isdigit():
            sql += f"\nLIMIT {limit}"

        return sql + ";"

