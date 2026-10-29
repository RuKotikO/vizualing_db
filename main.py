import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.views.main_window import MainWindow
from src.views.auth_window import AuthDialog, RegDialog
from src.models.sqlite_adapter import SQLiteAdapter


def log_uncaught_exceptions(ex_type, ex_value, ex_traceback):
    """Глобальный перехватчик, принудительно выводящий трассировку в консоль и окно."""
    error_msg = "".join(traceback.format_exception(ex_type, ex_value, ex_traceback))
    print("CRITICAL ERROR:\n", error_msg, file=sys.stderr)
    QMessageBox.critical(None, "Критическая ошибка", f"Приложение упало:\n{ex_value}")
    sys.exit(1)


# Регистрируем логер ошибок
sys.excepthook = log_uncaught_exceptions


def show_auth_flow(main_window, db_adapter):
    """Управляет циклом переключения окон авторизации и размытием заднего плана."""
    from PyQt6.QtWidgets import QGraphicsBlurEffect

    blur_effect = QGraphicsBlurEffect()
    blur_effect.setBlurRadius(15)
    main_window.centralWidget().setGraphicsEffect(blur_effect)

    while True:
        auth_dialog = AuthDialog(db_adapter, main_window)
        reg_dialog = RegDialog(db_adapter, main_window)

        auth_dialog.btn_to_reg.clicked.connect(auth_dialog.reject)
        auth_dialog.btn_to_reg.clicked.connect(reg_dialog.exec)
        reg_dialog.btn_to_auth.clicked.connect(reg_dialog.reject)

        result = auth_dialog.exec()

        if result == AuthDialog.DialogCode.Accepted:
            # Передаем управление локальной БД главному окну только ПОСЛЕ успешного входа
            main_window.init_database_behavior(db_adapter)
            break

        if reg_dialog.result() == RegDialog.DialogCode.Accepted:
            continue

        if auth_dialog.result() == AuthDialog.DialogCode.Rejected and not reg_dialog.isVisible():
            db_adapter.disconnect()
            sys.exit(0)

    main_window.centralWidget().setGraphicsEffect(None)


def main():
    app = QApplication(sys.argv)

    # Загрузка внешней изолированной таблицы стилей QSS
    try:
        with open("src/views/styles.qss", "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Предупреждение: Файл styles.qss не найден.")

    # Запуск локальной базы для хранения сессий авторизации и профилей
    db_adapter = SQLiteAdapter("app_internal.db")
    db_adapter.connect()

    # Инициализация интерфейса
    main_window = MainWindow()
    main_window.show()

    # Запуск блокирующего модального флоу
    show_auth_flow(main_window, db_adapter)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
