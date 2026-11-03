import os
import sys
from unittest.mock import MagicMock

# Жестко прописываем пути к корню и к самой папке src
sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../../src'))

# Инициализация фиктивного QApplication для PyQt6 виджетов
try:
    from PyQt6.QtWidgets import QApplication
    if not QApplication.instance():
        _sphinx_app = QApplication([])
except Exception:
    pass

# Изолируем внешние тяжелые библиотеки
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.OperationalError'] = MagicMock()

# -- Остальные настройки проекта (project, extensions, html_theme) остаются без изменений --

# 3. Полный список внешних модулей для изоляции импорта (MOCK)
# Добавляем сюда абсолютно все сторонние зависимости, кроме стандартной библиотеки и PyQt6
MOCK_MODULES = [
    'psycopg2',
    'psycopg2.OperationalError',
]
for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = MagicMock()

# -- Project information -----------------------------------------------------
project = 'DBSchemaVisualizer'
copyright = '2026, Роман'
author = 'Роман'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',      # Интроспекция docstrings
    'sphinx.ext.napoleon',     # Чтение Google/NumPy стилей
    'sphinx.ext.viewcode',     # Ссылки на исходный код
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'ru'

# Настройки генерации контента
autodoc_default_options = {
    'members': True,           # Выводить все функции и классы
    'undoc-members': True,     # Выводить даже те элементы, у которых нет docstring
    'special-members': '__init__', # Обязательно документировать конструкторы
    'show-inheritance': True,   # Показывать наследование (например, от QMainWindow)
}

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
