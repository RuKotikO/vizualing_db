import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import QMessageBox, QFileDialog
from PyQt6.QtCore import Qt

from src.views.auth_window import RegDialog, AuthDialog
from src.views.main_window import MainWindow
from src.views.dialogs.connection import NewConnectionDialog
from src.models.sqlite_adapter import SQLiteAdapter
from src.views.canvas.widgets import TableCardWidget
from src.models.data_classes import TableMetadata

# TC-01: Проверка поведения окна авторизации при отклонении (Rejected)
def test_tc01_auth_window_rejected(qtbot):
    """Физически проверяет, что окно авторизации корректно обрабатывает закрытие."""
    db_adapter = SQLiteAdapter("app_test_internal.db")
    db_adapter.connect()
    main_window = MainWindow()

    dialog = AuthDialog(db_adapter, main_window)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.reject()

    assert dialog.result() == AuthDialog.DialogCode.Rejected

    db_adapter.disconnect()
    if os.path.exists("app_test_internal.db"):
        os.remove("app_test_internal.db")

# TC-02: Валидация регистрационных данных пользователя (Короткий логин)
def test_tc02_registration_validation_short_login(qtbot, monkeypatch):
    """Физически проверяет валидацию: ввод данных -> клик -> QMessageBox."""
    db_adapter = SQLiteAdapter("app_test_internal.db")
    db_adapter.connect()

    dialog = RegDialog(db_adapter)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.login_input.setText("ru")
    dialog.password_input.setText("1234567")
    dialog.password_repeat_input.setText("1234567")

    warning_called = False

    def mock_warning(parent, title, text):
        nonlocal warning_called
        warning_called = True
        assert "не менее 3 символов" in text
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", mock_warning)

    qtbot.mouseClick(dialog.btn_register, Qt.MouseButton.LeftButton)

    assert warning_called is True
    db_adapter.disconnect()
    if os.path.exists("app_test_internal.db"):
        os.remove("app_test_internal.db")

# TC-03: Проверка обработки дубликатов пользователей при регистрации
def test_tc03_registration_duplicate_user(qtbot, monkeypatch):
    """Физически проверяет выдачу предупреждения, если логин уже занят."""
    db_adapter = SQLiteAdapter("app_test_internal.db")
    db_adapter.connect()

    db_adapter.register_user("tester", "password123")

    dialog = RegDialog(db_adapter)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.login_input.setText("tester")
    dialog.password_input.setText("7654321")
    dialog.password_repeat_input.setText("7654321")

    warning_called = False

    def mock_warning(parent, title, text):
        nonlocal warning_called
        warning_called = True
        assert "уже существует" in text
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "warning", mock_warning)

    qtbot.mouseClick(dialog.btn_register, Qt.MouseButton.LeftButton)

    assert warning_called is True
    db_adapter.disconnect()
    if os.path.exists("app_test_internal.db"):
        os.remove("app_test_internal.db")

# TC-04: Динамическое поведение полей ввода при смене типа СУБД (SQLite)
def test_tc04_connection_dialog_toggle_fields(qtbot):
    """Физически проверяет, что при выборе SQLite сетевые поля блокируются."""
    db_adapter = SQLiteAdapter("app_test_internal.db")
    db_adapter.connect()

    dialog = NewConnectionDialog(db_adapter, edit_title=None)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.host_input.setText("localhost")
    dialog.port_input.setText("5432")
    dialog.user_input.setText("postgres")

    dialog.combo_db_type.setCurrentText("SQLite")

    assert dialog.host_input.text() == ""
    assert dialog.port_input.text() == ""
    assert dialog.user_input.text() == ""
    assert dialog.host_input.isEnabled() is False
    assert dialog.port_input.isEnabled() is False
    assert dialog.user_input.isEnabled() is False

    db_adapter.disconnect()
    if os.path.exists("app_test_internal.db"):
        os.remove("app_test_internal.db")

# TC-05: Быстрый "живой" поиск таблиц на холсте
def test_tc05_live_table_search(qtbot):
    """Физически проверяет фильтрацию карточек таблиц при живом поиске."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)
    main_window.show()

    meta_tasks = TableMetadata(name="tasks")
    meta_users = TableMetadata(name="users")

    card_tasks = TableCardWidget(meta_tasks)
    card_users = TableCardWidget(meta_users)

    main_window.scene.addItem(card_tasks)
    main_window.scene.addItem(card_users)
    main_window.scene.cards = {"tasks": card_tasks, "users": card_users}

    main_window.search_input.setText("task")

    assert card_tasks.isVisible() is True
    assert card_users.isVisible() is False

# TC-06: Безопасная выгрузка данных выборки в JSON
def test_tc06_unload_data_json_flow(qtbot, monkeypatch, tmp_path):
    """Проверяет, что выгрузка в JSON корректно записывает структуру."""
    main_window = MainWindow()
    qtbot.addWidget(main_window)

    from PyQt6.QtGui import QStandardItemModel, QStandardItem
    model = QStandardItemModel(1, 2)
    model.setHorizontalHeaderLabels(["id", "title"])
    model.setItem(0, 0, QStandardItem("1"))
    model.setItem(0, 1, QStandardItem("TestTask"))
    main_window.results_table.setModel(model)

    target_file = os.path.join(tmp_path, "export.json")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args, **kwargs: (target_file, "Документ JSON (*.json)"))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)

    main_window.handle_unload_data()

    assert os.path.exists(target_file) is True
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == "1"
        assert data[0]["title"] == "TestTask"

# TC-07: Функция log_uncaught_exceptions / Глобальный перехватчик ошибок
def test_tc07_uncaught_exceptions_logger(monkeypatch):
    """Проверяет перехват критической ошибки без падения ОС."""
    from main import log_uncaught_exceptions

    critical_called = False

    def mock_critical(parent, title, text):
        nonlocal critical_called
        critical_called = True
        assert "Приложение упало" in text
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", mock_critical)

    exit_code = None
    import sys

    def mock_exit_code(code):
        nonlocal exit_code
        exit_code = code

    monkeypatch.setattr(sys, "exit", mock_exit_code)

    try:
        raise ValueError("Тестовый сбой СУБД")
    except ValueError as e:
        ex_type, ex_value, ex_traceback = sys.exc_info()
        log_uncaught_exceptions(ex_type, ex_value, ex_traceback)

    assert critical_called is True
    assert exit_code == 1