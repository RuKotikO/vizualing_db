import sys, os, traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QStandardPaths
from src.views.main_window import MainWindow
from src.views.auth_window import AuthDialog, RegDialog
from src.models.sqlite_adapter import SQLiteAdapter


def log_uncaught_exceptions(ex_type, ex_value, ex_traceback):
    """Глобальный перехватчик, принудительно выводящий трассировку в консоль и окно."""
    error_msg = "".join(traceback.format_exception(ex_type, ex_value, ex_traceback))
    print("CRITICAL ERROR:\n", error_msg, file=sys.stderr)
    QMessageBox.critical(None, "Критическая ошибка", f"Приложение упало:\n{ex_value}")
    sys.exit(1)

sys.excepthook = log_uncaught_exceptions


def show_auth_flow(main_window, db_adapter):
    """Управляет циклом переключения окон авторизации и размытием заднего плана."""
    from PyQt6.QtWidgets import QGraphicsBlurEffect

    blur_effect = QGraphicsBlurEffect()
    blur_effect.setBlurRadius(15)
    main_window.centralWidget().setGraphicsEffect(blur_effect)

    auth_dialog = AuthDialog(db_adapter, main_window)
    reg_dialog = RegDialog(db_adapter, main_window)

    GO_TO_REG = 10
    GO_TO_AUTH = 11

    auth_dialog.btn_to_reg.clicked.connect(lambda: auth_dialog.done(GO_TO_REG))
    reg_dialog.btn_to_auth.clicked.connect(lambda: reg_dialog.done(GO_TO_AUTH))

    current_window = "auth"

    while True:
        if current_window == "auth":
            result = auth_dialog.exec()

            if result == AuthDialog.DialogCode.Accepted:

                main_window.current_session_user = auth_dialog.current_user_name
                main_window.init_database_behavior(db_adapter)
                break
            elif result == GO_TO_REG:
                current_window = "reg"
                continue

            else:

                db_adapter.disconnect()
                sys.exit(0)

        elif current_window == "reg":
            result = reg_dialog.exec()

            if result == RegDialog.DialogCode.Accepted or result == GO_TO_AUTH:
                current_window = "auth"
                continue
            else:
                current_window = "auth"
                continue

    main_window.centralWidget().setGraphicsEffect(None)



def main():
    app = QApplication(sys.argv)

    app.setApplicationName("db")
    app.setOrganizationName("DBSchemaVisualizer")

    try:
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        qss_path = os.path.join(base_path, "src", "views", "styles.qss")

        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Предупреждение: Файл styles.qss не найден по пути {qss_path}")

    app_data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not os.path.exists(app_data_dir):
        os.makedirs(app_data_dir, exist_ok=True)
    internal_db_path = os.path.join(app_data_dir, "app_internal.db")
    print(f"Служебная конфигурация запущена по пути: {internal_db_path}")

    db_adapter = SQLiteAdapter(internal_db_path)
    db_adapter.connect()

    main_window = MainWindow()
    main_window.show()

    while True:

        app.processEvents()

        show_auth_flow(main_window, db_adapter)

        exit_code = app.exec()

        if exit_code == 999:
            continue
        else:
            sys.exit(exit_code)


if __name__ == "__main__":
    main()
