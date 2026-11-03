from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QPen, QFont


class TableCardWidget(QGraphicsRectItem):
    def __init__(self, table_metadata, x=0, y=0, parent=None):
        super().__init__(parent)
        self.metadata = table_metadata
        self.name = table_metadata.name
        self.relations = []

        self.show_types = True

        self.width = 240
        self.header_height = 36
        self.row_height = 28
        self.height = self.header_height + (len(table_metadata.fields) * self.row_height)

        self.setRect(QRectF(0, 0, self.width, self.height))
        self.setPos(x, y)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def get_field_edge_points(self, field_name: str) -> dict[str, QPointF]:
        """
        ИСПРАВЛЕНО: Рассчитывает абсолютно точные мировые координаты левой и правой
        границ конкретной строки (ячейки) таблицы для аккуратного подведения линий связей.
        """
        current_y = self.header_height
        for field in self.metadata.fields:
            if field.name.lower() == field_name.lower():
                center_y_in_card = current_y + (self.row_height / 2)
                return {
                    "left": self.scenePos() + QPointF(0, center_y_in_card),
                    "right": self.scenePos() + QPointF(self.width, center_y_in_card)
                }
            current_y += self.row_height

        fallback_y = self.header_height + (self.row_height / 2)
        return {
            "left": self.scenePos() + QPointF(0, fallback_y),
            "right": self.scenePos() + QPointF(self.width, fallback_y)
        }

    def paint(self, painter, option, widget):
        card_rect = self.rect()
        painter.setPen(QPen(QColor("#475569"), 1.5))
        painter.setBrush(QBrush(QColor("#1E293B")))
        painter.drawRoundedRect(card_rect, 6, 6)

        header_rect = QRectF(card_rect.x(), card_rect.y(), card_rect.width(), float(self.header_height))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#334155")))
        painter.drawRoundedRect(header_rect, 6, 6)
        painter.drawRect(int(card_rect.x()), int(card_rect.y() + self.header_height - 6), int(card_rect.width()), 6)

        painter.setPen(QPen(QColor("#475569"), 1.5))
        painter.drawLine(int(card_rect.x()), int(self.header_height), int(card_rect.x() + card_rect.width()),
                         int(self.header_height))

        painter.setPen(QColor("#F8FAFC"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(header_rect.adjusted(12, 0, -12, 0),
                         int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), self.name)

        current_y = self.header_height
        font_field = QFont("Segoe UI", 10)

        for field in self.metadata.fields:
            if current_y > self.header_height:
                painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(int(card_rect.x()), int(current_y), int(card_rect.x() + card_rect.width()),
                                 int(current_y))

            text_x_offset = 12
            if field.is_pk:
                painter.setPen(QColor("#EAB308"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(int(card_rect.x() + text_x_offset), int(current_y + 18), "[PK]")
                text_x_offset += 32
            elif field.is_fk:
                painter.setPen(QColor("#94A3B8"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(int(card_rect.x() + text_x_offset), int(current_y + 18), "[FK]")
                text_x_offset += 32

            painter.setPen(QColor("#F8FAFC"))
            painter.setFont(font_field)
            painter.drawText(int(card_rect.x() + text_x_offset), int(current_y + 18), field.name)

            if self.show_types:
                painter.setPen(QColor("#64748B"))
                type_rect = QRectF(card_rect.x(), float(current_y), card_rect.width() - 12, float(self.row_height))
                painter.drawText(type_rect, int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight),
                                 field.data_type.lower())

            current_y += self.row_height

    def add_relation(self, relation_line):
        self.relations.append(relation_line)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            for relation in self.relations:
                relation.update_position()
        return super().itemChange(change, value)
