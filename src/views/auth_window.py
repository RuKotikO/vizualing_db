from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt


class AuthDialog(QDialog):
    def __init__(self, db_adapter, parent=None):
        super().__init__(parent)
        self.db_adapter = db_adapter
        self.setWindowTitle("Вход в аккаунт")
        self.setFixedSize(350, 250)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.lbl_title = QLabel("Вход в аккаунт")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        layout.addWidget(self.login_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.btn_login = QPushButton("Войти")
        layout.addWidget(self.btn_login)

        self.btn_to_reg = QPushButton("Нету аккаунта? Зарегистрируйтесь")
        self.btn_to_reg.setFlat(True)
        layout.addWidget(self.btn_to_reg)

        self.btn_login.setObjectName("accent_btn")
        self.btn_login.clicked.connect(self.handle_login)

    def handle_login(self):
        u, p = self.login_input.text().strip(), self.password_input.text()
        if not u or not p: return
        if self.db_adapter.authenticate_user(u, p):
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль!")


class RegDialog(QDialog):
    def __init__(self, db_adapter, parent=None):
        super().__init__(parent)
        self.db_adapter = db_adapter
        self.setWindowTitle("Регистрация")
        self.setFixedSize(350, 280)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.lbl_title = QLabel("Регистрация")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Логин")
        layout.addWidget(self.login_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.password_repeat_input = QLineEdit()
        self.password_repeat_input.setPlaceholderText("Повтор пароля")
        self.password_repeat_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_repeat_input)

        self.btn_register = QPushButton("Регистрация")
        layout.addWidget(self.btn_register)

        self.btn_to_auth = QPushButton("Есть аккаунт? Войти")
        self.btn_to_auth.setFlat(True)
        layout.addWidget(self.btn_to_auth)

        self.btn_register.setObjectName("accent_btn")
        self.btn_register.clicked.connect(self.handle_registration)

    def handle_registration(self):
        u = self.login_input.text().strip()
        p = self.password_input.text()
        pr = self.password_repeat_input.text()

        # 1. Проверка на заполнение всех полей
        if not u or not p or not pr:
            QMessageBox.warning(self, "Внимание", "Заполните все поля!")
            return

        # 2. Проверка длины логина (не менее 3 символов)
        if len(u) < 3:
            QMessageBox.warning(self, "Ошибка валидации", "Имя пользователя должно содержать не менее 3 символов!")
            return

        # 3. ПРОВЕРКА ДЛИНЫ ПАРОЛЯ (не менее 6 символов)
        if len(p) < 6:
            QMessageBox.warning(self, "Ошибка валидации", "Пароль должен быть не менее 6 символов!")
            return

        # 4. Проверка совпадения паролей
        if p != pr:
            QMessageBox.critical(self, "Ошибка", "Пароли не совпадают!")
            return

        # 5. Проверка существования пользователя в БД
        if self.db_adapter.is_user_exists(u):
            QMessageBox.warning(self, "Ошибка регистрации", f"Пользователь с логином '{u}' уже существует!")
            return

        # 6. Попытка регистрации
        if self.db_adapter.register_user(u, p):
            QMessageBox.information(self, "Успех", "Регистрация успешна!")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось зарегистрировать пользователя. Попробуйте другое имя.")
