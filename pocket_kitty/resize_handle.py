"""A tiny drag handle that scales the pet around its center."""

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ResizeHandle(QWidget):
    drag_started = Signal()
    scale_requested = Signal(int)
    drag_finished = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.dragging = False
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        self.setAccessibleName('Drag to resize Kitty and menu')
        self.setToolTip('Drag outward to enlarge, inward to shrink')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pet = self.parentWidget()
            self.anchor = QPointF(pet.mapToGlobal(pet.menu.center.toPoint()))
            self.start_vector = event.globalPosition() - self.anchor
            self.start_scale = pet.cat_scale
            self.dragging = True
            self.drag_started.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            vector = event.globalPosition() - self.anchor
            length_squared = QPointF.dotProduct(self.start_vector, self.start_vector)
            if length_squared > 1:
                ratio = QPointF.dotProduct(vector, self.start_vector) / length_squared
                self.scale_requested.emit(round(self.start_scale * ratio))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.drag_finished.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 28, self.height() / 28)
        painter.translate(7, 7)
        painter.scale(0.5, 0.5)
        painter.setPen(QPen(QColor('#d8c1d4'), 1))
        painter.setBrush(QColor('#fff5ef') if not self.underMouse() else QColor('#f3dfed'))
        painter.drawEllipse(QPointF(14, 14), 12, 12)
        painter.setPen(QPen(QColor('#967b9d'), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(8, 8), QPointF(20, 20))
        for start, end in [((8, 8), (13, 8)), ((8, 8), (8, 13)), ((20, 20), (15, 20)), ((20, 20), (20, 15))]:
            painter.drawLine(QPointF(*start), QPointF(*end))

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)
