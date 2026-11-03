import math
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
        self.from_card = from_card
        self.fk_field_name = fk_field_name
        self.to_card = to_card
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

        x_fk = self.from_card.scenePos().x()
        w_fk = self.from_card.width
        x_pk = self.to_card.scenePos().x()
        w_pk = self.to_card.width

        path = QPainterPath()

        if x_pk + w_pk < x_fk:
            p_start = pk_pts["right"]
            p_finish = fk_pts["left"]
            target_side = "left"

            mid_x = x_pk + w_pk + (x_fk - (x_pk + w_pk)) / 2

            path.moveTo(p_start)
            path.lineTo(mid_x, p_start.y())
            path.lineTo(mid_x, p_finish.y())
            path.lineTo(p_finish)

        elif x_fk + w_fk < x_pk:
            p_start = pk_pts["left"]
            p_finish = fk_pts["right"]
            target_side = "right"

            mid_x = x_fk + w_fk + (x_pk - (x_fk + w_fk)) / 2

            path.moveTo(p_start)
            path.lineTo(mid_x, p_start.y())
            path.lineTo(mid_x, p_finish.y())
            path.lineTo(p_finish)

        else:
            p_start = pk_pts["left"]
            p_finish = fk_pts["left"]
            target_side = "left"

            min_x = min(x_fk, x_pk)
            mid_x = min_x - 30

            path.moveTo(p_start)
            path.lineTo(mid_x, p_start.y())
            path.lineTo(mid_x, p_finish.y())
            path.lineTo(p_finish)

        arrow_size = 6
        if target_side == "left":
            path.moveTo(p_finish.x() - arrow_size, p_finish.y() - arrow_size)
            path.lineTo(p_finish)
            path.lineTo(p_finish.x() - arrow_size, p_finish.y() + arrow_size)
        else:
            path.moveTo(p_finish.x() + arrow_size, p_finish.y() - arrow_size)
            path.lineTo(p_finish)
            path.lineTo(p_finish.x() + arrow_size, p_finish.y() + arrow_size)

        self.setPath(path)


class DatabaseCanvasScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        # Изначально задаем дефолтный размер сцены
        self.setSceneRect(0, 0, 1000, 1000)
        self.cards = {}
        self.lines = []

    def clear_canvas(self):
        self.clear()
        self.cards.clear()
        self.lines.clear()
        self.setSceneRect(0, 0, 1000, 1000)

    def render_schema(self, schema_metadata, main_window=None):
        if main_window is not None:
            self.main_window_ref = main_window

        self.clear_canvas()
        if not schema_metadata:
            return

        total_tables = len(schema_metadata)
        max_columns = max(3, math.ceil(math.sqrt(total_tables)))

        start_x, start_y = 50, 50
        gap_x = 340
        gap_y = 60

        current_column = 0
        current_row_max_height = 0

        current_x = start_x
        current_y = start_y

        for t_name, t_meta in schema_metadata.items():
            card = TableCardWidget(t_meta, current_x, current_y)
            self.addItem(card)
            self.cards[t_name] = card

            if card.height > current_row_max_height:
                current_row_max_height = card.height

            current_column += 1
            if current_column >= max_columns:
                current_column = 0
                current_x = start_x
                current_y += current_row_max_height + gap_y
                current_row_max_height = 0
            else:
                current_x += gap_x

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

        br = self.itemsBoundingRect()
        if not br.isNull():
            br.adjust(-100, -100, 100, 100)
            self.setSceneRect(br)
