from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox, QCheckBox, \
    QMessageBox
from PyQt6.QtCore import Qt


class NewConnectionDialog(QDialog):
    """
    Модальное окно создания и ИЗМЕНЕНИЯ (UPDATE) подключения к СУБД.
    """

    def __init__(self, db_adapter, current_user_id=1, edit_title=None, parent=None):
        super().__init__(parent)
        self.db_adapter = db_adapter
        self.current_user_id = current_user_id
        self.edit_title = edit_title

        self.setWindowTitle("Параметры соединения")
        self.setFixedSize(550, 300)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.lbl_header = QLabel("<h3>Параметры нового соединения</h3>")
        layout.addWidget(self.lbl_header)

        top_row = QHBoxLayout()
        self.combo_db_type = QComboBox()
        self.combo_db_type.addItems(["PostgreSQL", "SQLite"])
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Название профиля")
        top_row.addWidget(self.combo_db_type)
        top_row.addWidget(self.title_input)
        layout.addLayout(top_row)

        fields_layout = QHBoxLayout()
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Хост")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Порт")
        self.db_name_input = QLineEdit()
        self.db_name_input.setPlaceholderText("Имя БД / Путь к файлу")
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Пользователь")
        fields_layout.addWidget(self.host_input)
        fields_layout.addWidget(self.port_input)
        fields_layout.addWidget(self.db_name_input)
        fields_layout.addWidget(self.user_input)
        layout.addLayout(fields_layout)

        bottom_row = QHBoxLayout()

        self.cb_save_connection = QCheckBox("Сохранить соединение")
        self.cb_save_connection.setChecked(True)
        bottom_row.addWidget(self.cb_save_connection)

        self.btn_connect = QPushButton("Сохранить")
        bottom_row.addStretch()
        bottom_row.addWidget(self.btn_connect)
        layout.addLayout(bottom_row)

        self.btn_connect.setObjectName("accent_btn")
        self.btn_connect.clicked.connect(self.handle_save)

        # Подключаем сигнал изменения типа БД к обработчику блокировки полей
        self.combo_db_type.currentTextChanged.connect(self.toggle_fields_by_db_type)

        if self.edit_title:
            self.lbl_header.setText("<h3>Изменение параметров соединения</h3>")
            self.load_existing_data()
        else:
            # Вызываем триггер вручную при создании нового окна, чтобы применить логику для дефолтного значения
            self.toggle_fields_by_db_type(self.combo_db_type.currentText())

    def toggle_fields_by_db_type(self, db_type: str):
        """Динамически блокирует сетевые поля, если выбрана SQLite."""
        is_sqlite = (db_type == "SQLite")

        # Если SQLite — выключаем поля, если PostgreSQL — включаем
        self.host_input.setDisabled(is_sqlite)
        self.port_input.setDisabled(is_sqlite)
        self.user_input.setDisabled(is_sqlite)

        # Очищаем заблокированные поля для аккуратности
        if is_sqlite:
            self.host_input.clear()
            self.port_input.clear()
            self.user_input.clear()

    def load_existing_data(self):
        query = "SELECT db_type, host, port, db_name, db_user, save_password FROM connections WHERE title = ? LIMIT 1;"
        res = self.db_adapter.execute_query(query, (self.edit_title,))
        if res:
            db_type, host, port, db_name, db_user, save_pwd = res[0]
            self.title_input.setText(self.edit_title)
            self.combo_db_type.setCurrentText(db_type)
            self.host_input.setText(host)
            self.port_input.setText(str(port))
            self.db_name_input.setText(db_name)
            self.user_input.setText(db_user)
            self.cb_save_connection.setChecked(bool(save_pwd))
            # Принудительно обновляем состояние полей после загрузки данных
            self.toggle_fields_by_db_type(db_type)

    def handle_save(self):
        t = self.title_input.text().strip()
        db_type = self.combo_db_type.currentText()
        h = self.host_input.text().strip()
        p = self.port_input.text().strip()
        n = self.db_name_input.text().strip()
        u = self.user_input.text().strip()

        save_val = 1 if self.cb_save_connection.isChecked() else 0

        if not t or not n:
            QMessageBox.warning(self, "Внимание", "Заполните название профиля и имя/путь БД!")
            return

        port = int(p) if p else 5432

        if self.edit_title:
            try:
                self.db_adapter.execute_query(
                    """UPDATE connections 
                       SET title = ?, db_type = ?, host = ?, port = ?, db_name = ?, db_user = ?, save_password = ? 
                       WHERE title = ?;""",
                    (t, db_type, h, port, n, u, save_val, self.edit_title)
                )
                success = True
            except Exception:
                success = False
        else:
            try:
                self.db_adapter.execute_query(
                    """INSERT INTO connections (title, user_id, db_type, host, port, db_name, db_user, save_password) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
                    (t, self.current_user_id, db_type, h, port, n, u, save_val)
                )
                success = True
            except Exception:
                success = False

        if success:
            self.accept()
