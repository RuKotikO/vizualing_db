from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QCheckBox, QComboBox, \
    QListWidget, QMessageBox, QListWidgetItem
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

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        left_panel.addWidget(QLabel("<b>Настройка условий</b>"))

        left_panel.addWidget(QLabel("Выберите таблицу:"))
        self.combo_table = QComboBox()
        left_panel.addWidget(self.combo_table)

        left_panel.addWidget(QLabel("Выводимое поле (SELECT):"))
        self.combo_fields = QComboBox()
        left_panel.addWidget(self.combo_fields)

        left_panel.addWidget(QLabel("Фильтр по колонке (WHERE):"))
        self.combo_filter_col = QComboBox()
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
        left_panel.addWidget(self.combo_sort)

        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("Лимит строк (LIMIT)...")
        left_panel.addWidget(self.limit_input)

        self.btn_add_rule = QPushButton("Добавить правило")
        left_panel.addWidget(self.btn_add_rule)

        main_layout.addLayout(left_panel, stretch=1)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("<b>Данные запроса (Двойной клик — удалить параметр)</b>"))

        self.rules_list = QListWidget()
        right_panel.addWidget(self.rules_list)

        for rule_text in self.query_data["raw_rules_text"]:
            item = QListWidgetItem(rule_text)
            if rule_text.startswith("🔍 Фильтр: "):
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                if "NOT (" in rule_text:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
            self.rules_list.addItem(item)

        bottom_options_layout = QHBoxLayout()
        bottom_options_layout.addStretch()

        self.btn_clear_all = QPushButton("🗑️")
        self.btn_clear_all.setToolTip("Очистить все правила")
        self.btn_clear_all.setFixedSize(30, 30)
        self.btn_clear_all.setObjectName("destructive_btn")
        bottom_options_layout.addWidget(self.btn_clear_all)

        right_panel.addLayout(bottom_options_layout)

        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setObjectName("accent_btn")
        right_panel.addWidget(self.btn_apply)

        main_layout.addLayout(right_panel, stretch=1)

        self.combo_table.currentTextChanged.connect(self.handle_table_changed)
        self.btn_add_rule.clicked.connect(self.handle_add_rule)
        self.rules_list.itemDoubleClicked.connect(self.handle_delete_selected)
        self.btn_clear_all.clicked.connect(self.handle_clear_all_rules)
        self.rules_list.itemChanged.connect(self.handle_rule_checkbox_changed)
        self.btn_apply.clicked.connect(self.accept)

    def set_schema_data(self, schema_metadata):
        self.schema_metadata = schema_metadata
        self.combo_table.clear()
        if not schema_metadata:
            return
        self.combo_table.addItems(list(schema_metadata.keys()))

    def handle_table_changed(self, table_name):
        if not table_name:
            return

        actual_table = None
        if self.query_data["selected_fields"]:
            actual_table = list(self.query_data["selected_fields"].keys())[0]
        elif self.query_data["raw_rules_text"]:
            for rule_text in self.query_data["raw_rules_text"]:
                for prefix in ["➕ Вывести: ", "🔍 Фильтр: ", "↕️ Сортировка по: "]:
                    if rule_text.startswith(prefix):
                        clean_text = rule_text.replace(prefix, "").replace("NOT (", "")
                        if "." in clean_text:
                            actual_table = clean_text.split(".")[0].strip()
                            break
                if actual_table:
                    break

        if actual_table and table_name != actual_table:
            self.combo_table.blockSignals(True)
            self.combo_table.setCurrentText(actual_table)
            self.combo_table.blockSignals(False)

            QMessageBox.warning(
                self,
                "Смена таблицы заблокирована",
                f"Вы уже настраиваете запрос для таблицы '{actual_table}'.\n"
                "Вы можете добавлять любые новые параметры для неё.\n\n"
                "Чтобы переключиться на другую таблицу, сначала удалите все правила из списка справа."
            )
            return

        self.combo_fields.blockSignals(True)
        self.combo_filter_col.blockSignals(True)
        self.combo_sort.blockSignals(True)

        self.combo_fields.clear()
        self.combo_fields.addItem("[Не выводить]")
        self.combo_fields.addItem("* [Выбрать все поля]")

        self.combo_filter_col.clear()
        self.combo_filter_col.addItem("[Без фильтра]")

        self.combo_sort.clear()
        self.combo_sort.addItem("[Без сортировки]")

        if table_name in self.schema_metadata:
            table_meta = self.schema_metadata[table_name]
            field_names = [field.name for field in table_meta.fields]

            self.combo_fields.addItems(field_names)
            self.combo_filter_col.addItems(field_names)
            self.combo_sort.addItems(field_names)

        self.combo_fields.blockSignals(False)
        self.combo_filter_col.blockSignals(False)
        self.combo_sort.blockSignals(False)

    def handle_add_rule(self):
        """Добавляет новое правило в структуру данных и на экран."""
        table = self.combo_table.currentText()
        if not table:
            return

        field = self.combo_fields.currentText()
        filter_col = self.combo_filter_col.currentText()
        operator = self.combo_operator.currentText()
        filter_val = self.filter_data_input.text().strip()
        sort_col = self.combo_sort.currentText()
        limit_val = self.limit_input.text().strip()

        any_rule_added = False

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

                msg = f"➕ Вывести: {table}.{actual_field}"
                self.rules_list.addItem(msg)
                self.query_data["raw_rules_text"].append(msg)
                any_rule_added = True
            else:
                if "*" not in self.query_data["selected_fields"][table] and actual_field not in \
                        self.query_data["selected_fields"][table]:
                    self.query_data["selected_fields"][table].append(actual_field)
                    msg = f"➕ Вывести: {table}.{actual_field}"
                    self.rules_list.addItem(msg)
                    self.query_data["raw_rules_text"].append(msg)
                    any_rule_added = True

            self.combo_fields.setCurrentIndex(0)

        if filter_col != "[Без фильтра]" and filter_val:
            val_formatted = f"'{filter_val}'" if not filter_val.isdigit() else filter_val
            condition = f"{table}.{filter_col} {operator} {val_formatted}"

            if condition not in self.query_data["filters"]:
                self.query_data["filters"].append(condition)
                msg = f"🔍 Фильтр: {condition}"


                item = QListWidgetItem(msg)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)

                self.rules_list.addItem(item)
                self.query_data["raw_rules_text"].append(msg)
                any_rule_added = True

                self.filter_data_input.clear()
                self.combo_filter_col.setCurrentIndex(0)

        if sort_col != "[Без сортировки]":
            sort_entry = f"{table}.{sort_col}"
            if sort_entry not in self.query_data["sort_fields"]:
                self.query_data["sort_fields"].append(sort_entry)
                msg = f"↕️ Сортировка по: {sort_entry}"
                self.rules_list.addItem(msg)
                self.query_data["raw_rules_text"].append(msg)
                any_rule_added = True

                self.combo_sort.setCurrentIndex(0)

        if limit_val and limit_val.isdigit():
            # Удаляем старый лимит из списка отображения, если он уже был добавлен ранее
            items_to_remove = [self.rules_list.item(i) for i in range(self.rules_list.count())
                               if self.rules_list.item(i).text().startswith("🛑 Лимит строк:")]
            for item in items_to_remove:
                self.rules_list.takeItem(self.rules_list.row(item))
                if item.text() in self.query_data["raw_rules_text"]:
                    self.query_data["raw_rules_text"].remove(item.text())

            self.query_data["limit"] = limit_val
            msg = f"🛑 Лимит строк: {limit_val}"
            self.rules_list.addItem(msg)
            self.query_data["raw_rules_text"].append(msg)
            any_rule_added = True

            # Очищаем поле ввода лимита
            self.limit_input.clear()

        # Если ничего не было заполнено, но кнопку нажали — даем подсказку пользователю
        if not any_rule_added:
            QMessageBox.information(
                self, "Пустое правило",
                "Вы не настроили ни одного параметра.\n\n"
                "Чтобы добавить правило, выберите поле в SELECT, "
                "заполните условия фильтра (со значением) или выберите поле сортировки."
            )

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

    def handle_clear_all_rules(self):
        """Полностью очищает все правила из интерфейса и внутренних структур данных."""
        if self.rules_list.count() == 0:
            return

        reply = QMessageBox.question(
            self, "Очистка запроса",
            "Вы уверены, что хотите полностью удалить все добавленные правила и параметры?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.rules_list.clear()

            self.query_data["selected_fields"].clear()
            self.query_data["filters"].clear()
            self.query_data["sort_fields"].clear()
            self.query_data["limit"] = None
            self.query_data["raw_rules_text"].clear()

            current_table = self.combo_table.currentText()
            if current_table:
                self.handle_table_changed(current_table)

    def handle_rule_checkbox_changed(self, item):
        """Динамически инвертирует конкретный фильтр при клике на его галочку."""
        text = item.text()
        if not text.startswith("🔍 Фильтр: "):
            return

        # Извлекаем чистое SQL условие из строки
        clean_condition = text.replace("🔍 Фильтр: ", "").strip()

        # Блокируем сигналы, чтобы изменение текста не вызвало зацикливание этого же метода
        self.rules_list.blockSignals(True)

        if item.checkState() == Qt.CheckState.Checked:
            # Если галочку поставили, а NOT еще нет — добавляем инверсию
            if not clean_condition.startswith("NOT ("):
                # Удаляем старое чистое условие из общего списка фильтров билдера
                if clean_condition in self.query_data["filters"]:
                    self.query_data["filters"].remove(clean_condition)

                # Собираем новое условие с NOT
                not_condition = f"NOT ({clean_condition})"
                self.query_data["filters"].append(not_condition)

                # Обновляем текст на экране и в кэше строк
                new_text = f"🔍 Фильтр: {not_condition}"
                if text in self.query_data["raw_rules_text"]:
                    idx = self.query_data["raw_rules_text"].index(text)
                    self.query_data["raw_rules_text"][idx] = new_text
                item.setText(new_text)
        else:
            # Если галочку сняли, а NOT присутствует — убираем его
            if clean_condition.startswith("NOT (") and clean_condition.endswith(")"):
                if clean_condition in self.query_data["filters"]:
                    self.query_data["filters"].remove(clean_condition)

                # Извлекаем внутренности из "NOT (условие)"
                unwrapped_condition = clean_condition[5:-1]
                self.query_data["filters"].append(unwrapped_condition)

                # Обновляем текст на экране
                new_text = f"🔍 Фильтр: {unwrapped_condition}"
                if text in self.query_data["raw_rules_text"]:
                    idx = self.query_data["raw_rules_text"].index(text)
                    self.query_data["raw_rules_text"][idx] = new_text
                item.setText(new_text)

        self.rules_list.blockSignals(False)
