from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QCheckBox, QComboBox, \
    QListWidget, QMessageBox
from PyQt6.QtCore import Qt


class QueryParamsDialog(QDialog):
    """Модальное окно детальной настройки параметров поискового SQL-запроса сторонней БД."""

    def __init__(self, parent_view_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры запроса")
        self.resize(750, 480)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.schema_metadata = {}

        self.query_data = parent_view_data if parent_view_data is not None else {
            "selected_fields": {},
            "filters": [],
            "sort_fields": [],
            "limit": None,
            "raw_rules_text": []
        }

        main_layout = QHBoxLayout(self)

        # Левая часть
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        left_panel.addWidget(QLabel("<b>Настройка условий</b>"))

        left_panel.addWidget(QLabel("Выберите таблицу:"))
        self.combo_table = QComboBox()
        left_panel.addWidget(self.combo_table)

        left_panel.addWidget(QLabel("Выводимое поле (SELECT):"))
        self.combo_fields = QComboBox()
        self.combo_fields.addItem("[Не выводить]")
        left_panel.addWidget(self.combo_fields)

        left_panel.addWidget(QLabel("Фильтр по колонке (WHERE):"))
        self.combo_filter_col = QComboBox()
        self.combo_filter_col.addItem("[Без фильтра]")
        left_panel.addWidget(self.combo_filter_col)

        left_panel.addWidget(QLabel("Оператор:"))
        self.combo_operator = QComboBox()
        self.combo_operator.addItems(["=", ">", "<", ">=", "<=", "!=", "LIKE"])
        left_panel.addWidget(self.combo_operator)

        self.filter_data_input = QLineEdit()
        self.filter_data_input.setPlaceholderText("Значение фильтра...")
        left_panel.addWidget(self.filter_data_input)

        left_panel.addWidget(QLabel("Сортировка по полю (ORDER BY):"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItem("[Без сортировки]")
        left_panel.addWidget(self.combo_sort)

        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("Лимит строк (LIMIT)...")
        left_panel.addWidget(self.limit_input)

        self.btn_add_rule = QPushButton("Добавить правило")
        left_panel.addWidget(self.btn_add_rule)

        main_layout.addLayout(left_panel, stretch=1)

        # Правая часть
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("<b>Данные запроса (Двойной клик — удалить параметр)</b>"))

        self.rules_list = QListWidget()
        right_panel.addWidget(self.rules_list)

        for rule_text in self.query_data["raw_rules_text"]:
            self.rules_list.addItem(rule_text)

        self.cb_not_condition = QCheckBox("Инвертировать условие (NOT)")
        right_panel.addWidget(self.cb_not_condition)

        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setObjectName("accent_btn")
        right_panel.addWidget(self.btn_apply)

        main_layout.addLayout(right_panel, stretch=1)

        # Подключение сигналов
        self.combo_table.currentTextChanged.connect(self.handle_table_changed)
        self.btn_add_rule.clicked.connect(self.handle_add_rule)
        self.rules_list.itemDoubleClicked.connect(self.handle_delete_selected)
        self.btn_apply.clicked.connect(self.accept)

        # Жесткая блокировка комбобокса, если окно открывается повторно с уже готовыми правилами
        if self.rules_list.count() > 0:
            self.combo_table.setEnabled(False)

    def set_schema_data(self, schema_metadata):
        self.schema_metadata = schema_metadata
        self.combo_table.clear()
        if not schema_metadata:
            return
        self.combo_table.addItems(list(schema_metadata.keys()))

    def handle_table_changed(self, table_name):
        if not table_name:
            return

        if self.rules_list.count() > 0:
            actual_table = None
            if self.query_data["selected_fields"]:
                actual_table = list(self.query_data["selected_fields"].keys())[0]
            elif self.query_data["raw_rules_text"]:
                first_rule = self.query_data["raw_rules_text"][0]
                if "." in first_rule:
                    parts = first_rule.split(".")
                    actual_table = parts[0].replace("➕ Вывести: ", "").replace("🔍 Фильтр: ", "").replace("NOT (",
                                                                                                         "").replace(
                        "↕️ Сортировка по: ", "").strip()

            if actual_table and table_name != actual_table:
                self.combo_table.blockSignals(True)
                self.combo_table.setCurrentText(actual_table)
                self.combo_table.blockSignals(False)

                QMessageBox.warning(
                    self,
                    "Смена таблицы заблокирована",
                    f"Вы уже настраиваете запрос для таблицы '{actual_table}'.\n"
                    "Чтобы выбрать другую таблицу, сначала удалите все правила из списка справа."
                )
                return

        self.combo_fields.clear()
        self.combo_fields.addItem("[Не выводить]")
        self.combo_fields.addItem("* [Выбрать все поля]")
        self.combo_filter_col.clear()
        self.combo_filter_col.addItem("[Без фильтра]")
        self.combo_sort.clear()
        self.combo_sort.addItem("[Без сортировки]")

        if table_name not in self.schema_metadata:
            return

        table_meta = self.schema_metadata[table_name]
        field_names = [field.name for field in table_meta.fields]

        self.combo_fields.addItems(field_names)
        self.combo_filter_col.addItems(field_names)
        self.combo_sort.addItems(field_names)

    def handle_add_rule(self):
        """Добавляет новое правило в структуру данных и на экран."""
        table = self.combo_table.currentText()
        if not table: return

        field = self.combo_fields.currentText()
        filter_col = self.combo_filter_col.currentText()
        operator = self.combo_operator.currentText()
        filter_val = self.filter_data_input.text().strip()
        sort_col = self.combo_sort.currentText()
        limit_val = self.limit_input.text().strip()

        if field != "[Не выводить]":
            actual_field = "*" if field == "* [Выбрать все поля]" else field

            if table not in self.query_data["selected_fields"]:
                self.query_data["selected_fields"][table] = []

            if actual_field == "*":
                self.query_data["selected_fields"][table] = ["*"]
                items_to_remove = [self.rules_list.item(i) for i in range(self.rules_list.count())
                                   if self.rules_list.item(i).text().startswith(f"➕ Вывести: {table}.")]
                for item in items_to_remove:
                    self.rules_list.takeItem(self.rules_list.row(item))
                    if item.text() in self.query_data["raw_rules_text"]:
                        self.query_data["raw_rules_text"].remove(item.text())
            else:
                if "*" in self.query_data["selected_fields"][table]:
                    return
                if actual_field in self.query_data["selected_fields"][table]:
                    return
                self.query_data["selected_fields"][table].append(actual_field)

            msg = f"➕ Вывести: {table}.{actual_field}"
            self.rules_list.addItem(msg)
            self.query_data["raw_rules_text"].append(msg)

        if filter_col != "[Без фильтра]" and filter_val:
            val_formatted = f"'{filter_val}'" if not filter_val.isdigit() else filter_val
            condition = f"{table}.{filter_col} {operator} {val_formatted}"
            if self.cb_not_condition.isChecked():
                condition = f"NOT ({condition})"

            if condition not in self.query_data["filters"]:
                self.query_data["filters"].append(condition)
                msg = f"🔍 Фильтр: {condition}"
                self.rules_list.addItem(msg)
                self.query_data["raw_rules_text"].append(msg)
                self.filter_data_input.clear()

        if sort_col != "[Без сортировки]":
            sort_entry = f"{table}.{sort_col}"
            if sort_entry not in self.query_data["sort_fields"]:
                self.query_data["sort_fields"].append(sort_entry)
                msg = f"↕️ Сортировка по: {sort_entry}"
                self.rules_list.addItem(msg)
                self.query_data["raw_rules_text"].append(msg)

        if limit_val and limit_val.isdigit():
            self.query_data["limit"] = limit_val
            msg = f"🛑 Лимит строк: {limit_val}"
            self.rules_list.addItem(msg)
            self.query_data["raw_rules_text"].append(msg)
            self.limit_input.clear()

        if self.rules_list.count() > 0:
            self.combo_table.setEnabled(False)

    def handle_delete_selected(self):
        """Интеллектуальное удаление правила из интерфейса и всех внутренних структур Python."""
        current_item = self.rules_list.currentItem()
        if not current_item:
            return

        text = current_item.text()

        if text in self.query_data["raw_rules_text"]:
            self.query_data["raw_rules_text"].remove(text)

        if text.startswith("➕ Вывести: "):
            clean = text.replace("➕ Вывести: ", "").strip()
            if "." in clean:
                t_name, f_name = clean.split(".", 1)
                if t_name in self.query_data["selected_fields"]:
                    if f_name in self.query_data["selected_fields"][t_name]:
                        self.query_data["selected_fields"][t_name].remove(f_name)
                    if not self.query_data["selected_fields"][t_name]:
                        del self.query_data["selected_fields"][t_name]

        elif text.startswith("🔍 Фильтр: "):
            clean = text.replace("🔍 Фильтр: ", "").strip()
            if clean in self.query_data["filters"]:
                self.query_data["filters"].remove(clean)

        elif text.startswith("↕️ Сортировка по: "):
            clean = text.replace("↕️ Сортировка по: ", "").strip()
            if clean in self.query_data["sort_fields"]:
                self.query_data["sort_fields"].remove(clean)

        elif text.startswith("🛑 Лимит строк: "):
            self.query_data["limit"] = None

        self.rules_list.takeItem(self.rules_list.row(current_item))

        if self.rules_list.count() == 0:
            self.combo_table.setEnabled(True)
            current_table = self.combo_table.currentText()
            if current_table:
                self.handle_table_changed(current_table)
