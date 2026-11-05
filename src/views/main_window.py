import csv
import json
import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QListWidget, QGraphicsView, QFileDialog,
    QTextEdit, QPushButton, QLabel, QCheckBox, QLineEdit, QTableView, QMessageBox
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPixmap, QPainter

from src.views.dialogs.query_params import QueryParamsDialog
from src.controllers.app_controller import AppController
from src.controllers.query_builder import QueryBuilder
from src.views.dialogs.connection import NewConnectionDialog
from src.views.canvas.scene import DatabaseCanvasScene

class MainWindow(QMainWindow):
    """Главное окно визуализатора DBSchemaVisualizer."""
    def __init__(self):
        """Инициализирует элементы управления, применяет стили и настраивает холст."""
        super().__init__()
        self.setWindowTitle("Визуализатор БД — DBSchemaVisualizer")
        self.resize(1024, 768)

        self.controller = AppController(self)
        self.db_adapter = None

        self.current_query_storage = {
            "selected_fields": {},
            "filters": [],
            "sort_fields": [],
            "limit": None,
            "raw_rules_text": []
        }

        main_container = QWidget()
        self.setCentralWidget(main_container)
        root_layout = QVBoxLayout(main_container)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        top_panel = QWidget()
        top_panel.setObjectName("top_panel")
        top_layout = QHBoxLayout(top_panel)
        top_layout.setContentsMargins(10, 10, 10, 10)

        self.lbl_connection_status = QLabel("Ожидание авторизации пользователя...")
        top_layout.addWidget(self.lbl_connection_status)
        top_layout.addStretch()

        self.btn_change_conn = QPushButton("Изменить соединение")
        self.btn_refresh_schema = QPushButton("Обновить схему")
        self.btn_disconnect = QPushButton("Отключиться")
        self.btn_delete_conn = QPushButton("Удалить соединение")
        self.btn_delete_conn.setObjectName("destructive_btn")

        top_layout.addWidget(self.btn_change_conn)
        top_layout.addWidget(self.btn_refresh_schema)
        top_layout.addWidget(self.btn_disconnect)
        top_layout.addWidget(self.btn_delete_conn)
        root_layout.addWidget(top_panel)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        root_layout.addWidget(main_splitter)

        left_panel = QWidget()
        left_panel.setObjectName("left_panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("<b>Подключения</b>"))
        self.btn_create_conn = QPushButton("+ Создать соединение")
        left_layout.addWidget(self.btn_create_conn)

        left_layout.addWidget(QLabel("<b>История:</b>"))
        self.history_list = QListWidget()
        left_layout.addWidget(self.history_list)

        left_layout.addWidget(QLabel("<b>Сохранённые:</b>"))
        self.saved_list = QListWidget()
        left_layout.addWidget(self.saved_list)
        main_splitter.addWidget(left_panel)

        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)

        vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        center_layout.addWidget(vertical_splitter)

        self.scene = DatabaseCanvasScene()
        self.canvas_view = QGraphicsView(self.scene)
        self.canvas_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        def custom_wheel_event(event):
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                zoom_in_factor = 1.15
                zoom_out_factor = 1 / zoom_in_factor
                if event.angleDelta().y() > 0:
                    self.canvas_view.scale(zoom_in_factor, zoom_in_factor)
                else:
                    self.canvas_view.scale(zoom_out_factor, zoom_out_factor)
                event.accept()

            elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                scroll_step = event.angleDelta().y()
                h_bar = self.canvas_view.horizontalScrollBar()
                h_bar.setValue(h_bar.value() - scroll_step)
                event.accept()

            else:
                QGraphicsView.wheelEvent(self.canvas_view, event)

        self.canvas_view.wheelEvent = custom_wheel_event
        vertical_splitter.addWidget(self.canvas_view)

        bottom_panel = QWidget()
        bottom_panel.setObjectName("bottom_panel")
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(8)

        sql_header_layout = QHBoxLayout()
        sql_header_layout.addWidget(QLabel("<b>SQL запрос</b>"))
        sql_header_layout.addStretch()
        self.btn_params = QPushButton("Параметры")
        sql_header_layout.addWidget(self.btn_params)
        bottom_layout.addLayout(sql_header_layout)

        self.sql_text_edit = QTextEdit()
        self.sql_text_edit.setPlaceholderText("Здесь будет автоматически генерироваться SQL код...")
        self.sql_text_edit.setMaximumHeight(80)
        bottom_layout.addWidget(self.sql_text_edit)

        self.btn_execute = QPushButton("Выполнить")
        bottom_layout.addWidget(self.btn_execute)

        self.results_table = QTableView()
        bottom_layout.addWidget(self.results_table)
        vertical_splitter.addWidget(bottom_panel)
        main_splitter.addWidget(center_container)

        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        right_layout.addWidget(QLabel("<b>Фильтр</b>"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Быстрый поиск...")
        right_layout.addWidget(self.search_input)

        self.cb_types = QCheckBox("Типы данных")
        self.cb_links = QCheckBox("Линии связей")
        right_layout.addWidget(self.cb_types)
        right_layout.addWidget(self.cb_links)
        right_layout.addSpacing(15)

        right_layout.addWidget(QLabel("Управлять диаграммой:"))
        self.btn_export = QPushButton("Экспорт")
        right_layout.addWidget(self.btn_export)
        right_layout.addSpacing(15)

        right_layout.addWidget(QLabel("Выгрузить данные:"))
        self.btn_unload = QPushButton("Выгрузка")
        right_layout.addWidget(self.btn_unload)
        right_layout.addStretch()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([200, 624, 200])
        vertical_splitter.setSizes([500, 268])

        self.btn_params.clicked.connect(self.open_query_params_dialog)
        self.btn_execute.clicked.connect(self.handle_execute_query)
        self.search_input.textChanged.connect(self.handle_live_table_search)
        self.btn_export.clicked.connect(self.handle_export_diagram)
        self.btn_unload.clicked.connect(self.handle_unload_data)

    def init_database_behavior(self, db_adapter):
        """Вызывается строго после успешной авторизации пользователя."""
        self.db_adapter = db_adapter
        self.lbl_connection_status.setText("Авторизован в системе. Подключение к сторонней БД отсутствует.")

        self.btn_create_conn.clicked.connect(self.open_create_connection_dialog)
        self.refresh_connection_history()

        self.history_list.itemClicked.connect(self.handle_history_item_clicked)
        self.saved_list.itemClicked.connect(self.handle_history_item_clicked)

        self.history_list.itemClicked.connect(lambda: self.saved_list.clearSelection())
        self.saved_list.itemClicked.connect(lambda: self.history_list.clearSelection())

        self.btn_disconnect.clicked.connect(self.handle_disconnect)
        self.btn_refresh_schema.clicked.connect(self.handle_refresh_schema)
        self.btn_delete_conn.clicked.connect(self.handle_delete_connection)
        self.btn_change_conn.clicked.connect(self.handle_change_connection)

        self.cb_types.setChecked(True)
        self.cb_links.setChecked(True)
        self.cb_types.stateChanged.connect(self.handle_toggle_types)
        self.cb_links.stateChanged.connect(self.handle_toggle_links)

    def init_database_behavior(self, db_adapter):
        """Вызывается строго после успешной авторизации пользователя."""
        self.db_adapter = db_adapter
        self.lbl_connection_status.setText("Авторизован в системе. Подключение к сторонней БД отсутствует.")

        self.btn_create_conn.clicked.connect(self.open_create_connection_dialog)
        self.refresh_connection_history()

        self.history_list.itemClicked.connect(self.handle_history_item_clicked)
        self.saved_list.itemClicked.connect(self.handle_history_item_clicked)

        self.history_list.itemClicked.connect(lambda: self.saved_list.clearSelection())
        self.saved_list.itemClicked.connect(lambda: self.history_list.clearSelection())

        self.btn_disconnect.clicked.connect(self.handle_disconnect)
        self.btn_refresh_schema.clicked.connect(self.handle_refresh_schema)
        self.btn_delete_conn.clicked.connect(self.handle_delete_connection)
        self.btn_change_conn.clicked.connect(self.handle_change_connection)

        self.cb_types.setChecked(True)
        self.cb_links.setChecked(True)
        self.cb_types.stateChanged.connect(self.handle_toggle_types)
        self.cb_links.stateChanged.connect(self.handle_toggle_links)

    def open_create_connection_dialog(self):
        dialog = NewConnectionDialog(self.db_adapter, current_user_id=1, parent=self)
        if dialog.exec() == NewConnectionDialog.DialogCode.Accepted:
            self.clear_current_query_data()
            self.refresh_connection_history()

    def open_query_params_dialog(self):

        dialog = QueryParamsDialog(parent_view_data=self.current_query_storage, parent=self)

        active_schema = self.controller.get_active_schema()
        dialog.set_schema_data(active_schema)

        if dialog.exec() == QueryParamsDialog.DialogCode.Accepted:
            if not self.current_query_storage["selected_fields"]:
                self.sql_text_edit.clear()
                QMessageBox.warning(self, "Внимание", "Вы удалили все поля для вывода (SELECT)!")
                return

            builder = QueryBuilder(self.controller.active_metadata)
            try:
                sql_code = builder.build_complex_select(
                    selected_fields=self.current_query_storage["selected_fields"],
                    filters=self.current_query_storage["filters"],
                    sort_fields=self.current_query_storage["sort_fields"],
                    limit=self.current_query_storage["limit"]
                )
                self.sql_text_edit.setPlainText(sql_code)
            except Exception as e:
                self.sql_text_edit.setPlainText(f"-- Ошибка генерации комплексного запроса: {e}")

    def refresh_connection_history(self):
        """Обновление истории профилей из локальной SQLite."""
        self.history_list.clear()
        self.saved_list.clear()

        query_all = "SELECT id, title, host, port, db_name, db_type FROM connections WHERE user_id = 1;"
        all_profiles = self.db_adapter.execute_query(query_all)

        for p in all_profiles:
            p_id, title, host, port, db_name, db_type = p
            icon = "🐘 [PG]" if db_type == "PostgreSQL" else "🗄️ [Lite]"

            if db_type == "SQLite":
                self.history_list.addItem(f"{icon} {title} (Локальный файл)")
            else:
                self.history_list.addItem(f"{icon} {title} ({host}:{port})")

        saved_query = "SELECT title, db_type FROM connections WHERE user_id = ? AND save_password = 1;"
        saved_profiles = self.db_adapter.execute_query(saved_query, (1,))

        for row in saved_profiles:
            title, db_type = row
            icon = "🐘 [PG]" if db_type == "PostgreSQL" else "🗄️ [Lite]"
            self.saved_list.addItem(f"{icon} {title}")

    def handle_history_item_clicked(self, item):
        """Безопасное извлечение параметров и динамическое подключение к СУБД."""
        text = item.text()

        clean_text = text.replace("🐘 [PG] ", "").replace("🗄️ [Lite] ", "").strip()

        if "(" in clean_text:
            title = clean_text.split("(")[0].strip()
        else:
            title = clean_text

        if self.controller and self.controller.active_connector and self.controller.active_connector.conn:
            if title in self.lbl_connection_status.text():
                return

            reply = QMessageBox.question(
                self, "Смена подключения",
                "Вы уверены, что хотите отсоединиться от текущей базы данных и переключиться на новую?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                self.history_list.clearSelection()
                self.saved_list.clearSelection()
                return

        self.clear_current_query_data()

        query = "SELECT db_type, host, port, db_name, db_user FROM connections WHERE title = ? LIMIT 1;"
        res_list = self.db_adapter.execute_query(query, (title,))

        if not res_list:
            QMessageBox.warning(self, "Внимание", f"Профиль '{title}' не найден in локальной БД!")
            return

        row = res_list[0]
        db_type, host, port, db_name, db_user = row

        if db_type == "SQLite":
            db_name = db_name.strip("'\"")

            self.lbl_connection_status.setText(f"Открытие локального файла базы данных: {db_name}...")
            self.lbl_connection_status.repaint()

            if not os.path.exists(db_name):
                try:
                    dropdown_dir = os.path.dirname(db_name)
                    if dropdown_dir and not os.path.exists(dropdown_dir):
                        os.makedirs(dropdown_dir,
                                    exist_ok=True)
                    with open(db_name, 'w') as f:
                        pass
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка файловой системы", f"Не удалось открыть файл:\n{e}")
                    return

            success = self.controller.connect_to_database(db_type="SQLite", database=db_name)

        else:
            self.lbl_connection_status.setText(f"Установка сетевого соединения с {host}:{port}...")
            self.lbl_connection_status.repaint()
            success = self.controller.connect_to_database(
                db_type="PostgreSQL", host=host, port=int(port), database=db_name, user=db_user,
                password="your_postgres_password"
            )

        if success:
            self.lbl_connection_status.setText(f"🔌 Активная база данных [{db_type}]: {db_name} (Профиль: {title})")
            if self.db_adapter:
                self.db_adapter.log_message("INFO", f"Пользователь переключился на БД {db_name} ({db_type})")

            if self.scene.cards:
                first_card = list(self.scene.cards.values())[0]
                self.canvas_view.centerOn(first_card)
        else:
            QMessageBox.critical(self, "Ошибка СУБД", f"Не удалось открыть базу данных: {db_name}")

    def handle_disconnect(self):
        """Безопасно разрывает сетевое соединение со сторонней БД и очищает холст."""
        if not self.controller or not self.controller.active_connector:
            QMessageBox.critical(self, "Внимание",
                                    "Активное подключение к базе данных отсутствует. Нечего отключать!")
            return

        try:
            self.controller.active_connector.disconnect()
        except Exception as e:
            print(f"Ошибка при закрытии соединения: {e}")

        self.controller.active_metadata.clear()
        self.scene.clear_canvas()

        self.clear_current_query_data()

        self.lbl_connection_status.setText("Отключено от сторонней СУБД. Холст очищен.")
        if self.db_adapter:
            self.db_adapter.log_message("INFO", "Пользователь вручную разорвал сетевое соединение")

    def handle_refresh_schema(self):
        """Повторно вычитывает системные каталоги СУБД и перерисовывает схему."""
        if not self.controller.active_connector or not self.controller.active_connector.conn:
            QMessageBox.warning(self, "Внимание", "Нет активного подключения для обновления схемы!")
            return

        try:
            metadata = self.controller.active_connector.get_schema_metadata()
            self.controller.active_metadata = metadata

            self.scene.render_schema(metadata, self)
            self.lbl_connection_status.setText(f"Схема СУБД успешно обновлена.")
        except Exception as e:
            self.lbl_connection_status.setText(f"Ошибка обновления схемы: {e}")

    def handle_delete_connection(self):
        """Удаляет выбранное в сайдбаре подключение (из Истории или Сохранённых) из локальной БД."""
        active_list = None
        if self.history_list.currentItem() is not None:
            active_list = self.history_list
        elif self.saved_list.currentItem() is not None:
            active_list = self.saved_list

        if not active_list or active_list.currentItem() is None:
            QMessageBox.warning(self, "Внимание",
                                "Выберите профиль подключения из списка Истории или Сохранённых для удаления!")
            return

        current_item = active_list.currentItem()
        text = current_item.text()

        clean_text = text.replace("🐘 [PG] ", "").replace("🗄️ [Lite] ", "").replace("🔌 ", "").strip()
        if "(" in clean_text:
            title = clean_text.split("(")[0].strip()
        else:
            title = clean_text

        reply = QMessageBox.question(
            self, "Удаление", f"Вы уверены, что хотите полностью удалить профиль '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.db_adapter.delete_connection_profile(title):
                current_status = self.lbl_connection_status.text()

                if title in current_status:
                    if self.controller and self.controller.active_connector:
                        try:
                            self.handle_disconnect()
                        except Exception:
                            pass
                    else:
                        self.scene.clear_canvas()
                        self.clear_current_query_data()
                        self.lbl_connection_status.setText("Профиль удален. Холст очищен.")

                self.history_list.clearSelection()
                self.saved_list.clearSelection()
                self.history_list.setCurrentItem(None)
                self.saved_list.setCurrentItem(None)

                self.refresh_connection_history()

                QMessageBox.information(self, "Успех", f"Профиль '{title}' успешно удален.")
            else:
                QMessageBox.critical(self, "Ошибка",
                                     f"Не удалось удалить профиль '{title}' из базы данных конфигураций.")

    def handle_change_connection(self):
        """Открывает окно изменения параметров (UPDATE) для выбранного соединения."""
        current_item = self.history_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Внимание", "Выберите подключение из списка истории для изменения!")
            return

        text = current_item.text()

        clean_text = text.replace("🐘 [PG] ", "").replace("🗄️ [Lite] ", "").strip()

        bracket_index = clean_text.find(" (")
        title = clean_text[:bracket_index].strip() if bracket_index != -1 else clean_text.strip()

        dialog = NewConnectionDialog(self.db_adapter, current_user_id=1, edit_title=title, parent=self)
        if dialog.exec() == NewConnectionDialog.DialogCode.Accepted:
            self.refresh_connection_history()
            QMessageBox.information(self, "Успех", f"Профиль '{title}' успешно изменен.")

    def handle_toggle_types(self, state):
        """Реактивно скрывает/показывает типы данных на карточках холста."""
        is_checked = (state == 2)
        for card in self.scene.cards.values():
            card.show_types = is_checked
            card.update()

    def handle_toggle_links(self, state):
        """Реактивно скрывает/показывает линии связей на холсте."""
        is_checked = (state == 2)
        for line in self.scene.lines:
            line.setVisible(is_checked)

    def handle_execute_query(self):
        """
        Передает автоматически сгенерированный SQL-код в активный драйвер СУБД,
        получает структурированный ответ и визуализирует выборку в виджете QTableView.
        """
        if not self.controller.active_connector or not self.controller.active_connector.conn:
            QMessageBox.warning(self, "Внимание", "Отсутствует активное подключение к базе данных!")
            return

        sql_text = self.sql_text_edit.toPlainText().strip()
        if not sql_text or sql_text.startswith("--"):
            QMessageBox.warning(self, "Внимание", "Текст SQL-запроса пуст или содержит ошибку параметров!")
            return

        cursor = None
        try:
            connector = self.controller.active_connector
            cursor = connector.conn.cursor()
            cursor.execute(sql_text)

            if cursor.description:
                column_names = [str(desc[0]) for desc in cursor.description]
                rows = cursor.fetchall()

                model = QStandardItemModel(len(rows), len(column_names))
                model.setHorizontalHeaderLabels(column_names)

                for row_idx, row_data in enumerate(rows):
                    for col_idx, cell_value in enumerate(row_data):
                        val_str = str(cell_value) if cell_value is not None else "NULL"
                        item = QStandardItem(val_str)
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        model.setItem(row_idx, col_idx, item)

                self.results_table.setModel(model)
                self.results_table.resizeColumnsToContents()

                self.lbl_connection_status.setText(f"Запрос успешно выполнен. Выведено строк: {len(rows)}.")
                if self.db_adapter:
                    self.db_adapter.log_message("INFO", f"Успешно выполнен SELECT-запрос: {sql_text[:50]}...")
            else:
                connector.conn.commit()
                self.lbl_connection_status.setText("Запрос выполнен успешно (данные не возвращены).")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выполнения SQL", f"СУБД вернула ошибку:\n{e}")
            self.lbl_connection_status.setText("Ошибка при выполнении SQL-кода.")
            if self.db_adapter:
                self.db_adapter.log_message("ERROR", f"Сбой выполнения запроса: {e}")

        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass

    def clear_current_query_data(self):
        """Полностью обнуляет параметры текущего SQL-запроса и очищает интерфейс вывода."""
        self.current_query_storage = {
            "selected_fields": {},
            "filters": [],
            "sort_fields": [],
            "limit": None,
            "raw_rules_text": []
        }
        self.sql_text_edit.clear()

        if self.results_table.model() is not None:
            self.results_table.setModel(None)

    def handle_live_table_search(self, search_text):
        """
        Динамически фильтрует карточки таблиц на холсте.
        Скрывает те, чьи имена не содержат введенный пользователем текст.
        """
        search_text = search_text.strip().lower()

        if not search_text:
            for card in self.scene.cards.values():
                card.setVisible(True)
            self.handle_toggle_links(self.cb_links.checkState().value)
            return

        for t_name, card in self.scene.cards.items():
            if search_text in t_name.lower():
                card.setVisible(True)
            else:
                card.setVisible(False)

        for line in self.scene.lines:
            if line.from_card.isVisible() and line.to_card.isVisible() and self.cb_links.isChecked():
                line.setVisible(True)
            else:
                line.setVisible(False)

    def handle_export_diagram(self):
        """
        Рендерит интерактивный холст со схемой БД в растровое изображение высокого
        разрешения и сохраняет его в файл формата PNG через QFileDialog.
        """
        if not self.scene.cards:
            QMessageBox.warning(self, "Внимание", "На холсте нет отображаемой схемы для экспорта!")
            return


        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт диаграммы структуры БД", "db_schema_export.png", "Изображения (*.png)"
        )

        if not file_path:
            return

        try:
            items_rect = self.scene.itemsBoundingRect()

            items_rect.adjust(-20, -20, 20, 20)

            pixmap = QPixmap(int(items_rect.width()), int(items_rect.height()))
            pixmap.fill(Qt.GlobalColor.white)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter, QRectF(pixmap.rect()), items_rect)
            painter.end()

            if pixmap.save(file_path, "PNG"):
                QMessageBox.information(self, "Успех",
                                        f"Диаграмма структуры успешно экспортирована в файл:\n{file_path}")
                self.db_adapter.log_message("INFO", f"Экспортирована схема в графический файл {file_path}")
            else:
                raise Exception("Ошибка записи файла модулем QPixmap.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить изображение схемы:\n{e}")

    def handle_unload_data(self):
        """
        Выгружает текущие строки из QTableView в файлы форматов CSV или JSON
        в зависимости от выбора пользователя в диалоговом окне сохранения.
        """
        model = self.results_table.model()
        if model is None or model.rowCount() == 0:
            QMessageBox.warning(self, "Внимание", "В таблице результатов нет данных для выгрузки!")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Выгрузка данных выборки", "exported_data.csv",
            "Таблица CSV (*.csv);;Документ JSON (*.json)"
        )

        if not file_path:
            return

        try:
            headers = [model.headerData(c, Qt.Orientation.Horizontal) for c in range(model.columnCount())]
            data_rows = [[model.item(r, c).text() if model.item(r, c) else "" for c in range(model.columnCount())] for r
                         in range(model.rowCount())]

            if file_path.endswith(".json") or "JSON" in selected_filter:
                json_data = [dict(zip(headers, row)) for row in data_rows]

                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=4)

                QMessageBox.information(self, "Успех", f"Данные успешно выгружены в формате JSON:\n{file_path}")
                if self.db_adapter:
                    self.db_adapter.log_message("INFO", f"Выгружены данные выборки в JSON: {file_path}")
                return

            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(headers)
                writer.writerows(data_rows)

            QMessageBox.information(self, "Успех", f"Данные успешно выгружены в формате CSV:\n{file_path}")
            if self.db_adapter:
                self.db_adapter.log_message("INFO", f"Выгружены данные выборки в CSV: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выгрузки", f"Не удалось выполнить выгрузку данных в файл:\n{e}")

