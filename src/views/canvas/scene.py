from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PyQt6.QtCore import QPointF, Qt, QRectF
from PyQt6.QtGui import QPen, QColor, QPainterPath
from src.views.canvas.widgets import TableCardWidget


class RelationLineItem(QGraphicsPathItem):
    """
    Ортогональная линия связи с углами под 90 градусов.
    Визуально идет ОТ родителя [PK] К дочернему [FK].
    """

    def __init__(self, from_card, fk_field_name, to_card, pk_field_name="id", parent=None):
        super().__init__(parent)
        self.from_card = from_card  # Технически: дочерняя (FK)
        self.fk_field_name = fk_field_name
        self.to_card = to_card  # Технически: родительская (PK)
        self.pk_field_name = pk_field_name

        self.setPen(
            QPen(QColor("#6366F1"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))

        self.from_card.add_relation(self)
        self.to_card.add_relation(self)
        self.update_position()

    def update_position(self):
        """Строит идеальный ортогональный путь под 90 градусов от PK к FK, огибая карточки."""
        fk_pts = self.from_card.get_field_edge_points(self.fk_field_name)
        pk_pts = self.to_card.get_field_edge_points(self.pk_field_name)

        # Координаты и размеры карточек для точного расчёта зазоров
        x_fk = self.from_card.scenePos().x()
        w_fk = self.from_card.width
        x_pk = self.to_card.scenePos().x()
        w_pk = self.to_card.width

        path = QPainterPath()

        # СЦЕНАРИЙ 1: Карточка PK находится ЛЕВЕЕ карточки FK
        if x_pk + w_pk < x_fk:
            p_start = pk_pts["right"]  # Выходим справа из PK
            p_finish = fk_pts["left"]  # Заходим слева в FK
            target_side = "left"

            # Центральная ось — строго посередине пустого пространства МЕЖДУ карточками
            mid_x = x_pk + w_pk + (x_fk - (x_pk + w_pk)) / 2

            path.moveTo(p_start)
            path.lineTo(mid_x, p_start.y())  # Горизонтальный выход на центральную ось
            path.lineTo(mid_x, p_finish.y())  # Вертикальный спуск/подъем до уровня FK
            path.lineTo(p_finish)  # Горизонтальный заход в FK

        # СЦЕНАРИЙ 2: Карточка PK находится ПРАВЕЕ карточки FK
        elif x_fk + w_fk < x_pk:
            p_start = pk_pts["left"]  # Выходим слева из PK
            p_finish = fk_pts["right"]  # Заходим справа в FK
            target_side = "right"

            # Центральная ось — строго посередине пустого пространства между ними
            mid_x = x_fk + w_fk + (x_pk - (x_fk + w_fk)) / 2

            path.moveTo(p_start)
            path.lineTo(mid_x, p_start.y())
            path.lineTo(mid_x, p_finish.y())
            path.lineTo(p_finish)

        # СЦЕНАРИЙ 3: Карточки выстроены вертикально друг под другом (или сильно перекрываются по X)
        else:
            p_start = pk_pts["left"]  # Выходим слева
            p_finish = fk_pts["left"]  # Заходим слева
            target_side = "left"

            # Выносим вертикальный мост левее самой левой карточки на фиксированный отступ 30px
            min_x = min(x_fk, x_pk)
            mid_x = min_x - 30

            path.moveTo(p_start)
            path.lineTo(mid_x, p_start.y())  # Усик влево наружу
            path.lineTo(mid_x, p_finish.y())  # Вертикальный шлейф сбоку от карточек
            path.lineTo(p_finish)  # Заход вправо в поле FK

        # 3. Отрисовка наконечника стрелочки (остриё всегда смотрит внутрь ячейки FK)
        arrow_size = 6
        if target_side == "left":
            # Заход в левую грань карточки -> стрелка указывает НАПРАВО ( > )
            path.moveTo(p_finish.x() - arrow_size, p_finish.y() - arrow_size)
            path.lineTo(p_finish)
            path.lineTo(p_finish.x() - arrow_size, p_finish.y() + arrow_size)
        else:
            # Заход в правую грань карточки -> стрелка указывает НАЛЕВО ( < )
            path.moveTo(p_finish.x() + arrow_size, p_finish.y() - arrow_size)
            path.lineTo(p_finish)
            path.lineTo(p_finish.x() + arrow_size, p_finish.y() + arrow_size)

        self.setPath(path)


class DatabaseCanvasScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        self.setSceneRect(0, 0, 2000, 2000)
        self.cards = {}
        self.lines = []

    def clear_canvas(self):
        self.clear()
        self.cards.clear()
        self.lines.clear()

    def render_schema(self, schema_metadata, main_window=None):
        if main_window is not None:
            self.main_window_ref = main_window

        self.clear_canvas()

        start_x, start_y = 450, 450
        gap_x = 340
        current_column = 0

        for t_name, t_meta in schema_metadata.items():
            card = TableCardWidget(t_meta, start_x + (current_column * gap_x), start_y)
            self.addItem(card)
            self.cards[t_name] = card

            current_column += 1
            if current_column >= 3:
                current_column = 0
                start_y += 280

        # Стабильный технический вызов для внутренней бизнес-логики SQL
        for table_name, table_meta in schema_metadata.items():
            for field in table_meta.fields:
                if field.is_fk and field.fk_info:
                    to_t = field.fk_info.to_table
                    to_f = field.fk_info.to_field if field.fk_info.to_field else "id"

                    if table_name in self.cards and to_t in self.cards:
                        line_item = RelationLineItem(
                            from_card=self.cards[table_name],
                            fk_field_name=field.name,
                            to_card=self.cards[to_t],
                            pk_field_name=to_f
                        )
                        self.addItem(line_item)
                        self.lines.append(line_item)
