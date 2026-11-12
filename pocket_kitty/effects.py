"""Small local Qt drawings and transforms driven by one action timeline."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRegion, QTransform
from PySide6.QtWidgets import QLabel, QWidget


class AnimatedCat(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.action = None
        self.progress = 0.0
        self.base_region = QRegion()

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.base_region = QRegion(pixmap.mask())

    def frame_transform(self) -> QTransform:
        transform = QTransform()
        if self.action is None:
            return transform
        wave = math.sin(self.progress * math.pi * 6)
        transform.translate(self.width() / 2, self.height() * 0.92)
        if self.action == 'Feed':
            chew = math.sin(max(0, self.progress - 0.45) * math.pi * 14)
            transform.translate(0, -abs(chew) * 2)
            transform.scale(1 + chew * 0.012, 1 - chew * 0.012)
        elif self.action == 'Pat':
            bounce = wave ** 2
            transform.translate(0, -bounce * 4)
            transform.scale(1 + bounce * 0.018, 1 - bounce * 0.018)
        elif self.action == 'Play':
            transform.translate(wave * 3, 0)
            transform.rotate(wave * 2.3)
        transform.translate(-self.width() / 2, -self.height() * 0.92)
        return transform

    def visual_region(self) -> QRegion:
        return self.frame_transform().map(self.base_region).translated(self.pos())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setTransform(self.frame_transform())
        pixmap = self.pixmap()
        if pixmap and not pixmap.isNull():
            painter.drawPixmap(0, 0, pixmap)


class SpeechBubble(QLabel):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#e9d7dc'), 1))
        painter.setBrush(QColor('#fff7ee'))
        path = QPainterPath()
        path.addRoundedRect(QRectF(1, 6, self.width() - 2, self.height() - 7), 14, 14)
        tail = QPainterPath(QPointF(self.width() / 2 - 6, 7))
        tail.lineTo(self.width() / 2 + 1, 0)
        tail.lineTo(self.width() / 2 + 7, 7)
        path = path.united(tail)
        painter.drawPath(path)
        painter.setPen(QColor('#58475f'))
        painter.setFont(QFont('Segoe UI', 10))
        painter.drawText(QRectF(8, 7, self.width() - 16, self.height() - 8), Qt.AlignmentFlag.AlignCenter, self.text())


def draw_effect(painter: QPainter, kind: str) -> None:
    """Draw one icon in a 32 by 32 local coordinate system."""
    painter.setPen(QPen(QColor('#997b96'), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    path = QPainterPath()
    if kind == 'Feed':
        painter.setBrush(QColor('#8fcbe4'))
        path.moveTo(10, 16)
        path.lineTo(1, 6)
        path.lineTo(1, 26)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawEllipse(QRectF(7, 7, 24, 18))
        painter.setBrush(QColor('#58475f'))
        painter.drawEllipse(QRectF(24, 12, 2, 2))
    elif kind == 'Pat':
        painter.setBrush(QColor('#f39bbb'))
        path.moveTo(16, 29)
        path.cubicTo(-12, 12, 6, -3, 16, 8)
        path.cubicTo(26, -3, 44, 12, 16, 29)
        painter.drawPath(path)
    else:
        painter.setBrush(QColor('#f3bc99'))
        path.moveTo(5, 27)
        path.cubicTo(0, 6, 16, 0, 30, 2)
        path.cubicTo(32, 17, 23, 28, 5, 27)
        painter.drawPath(path)
        painter.drawLine(QPointF(1, 32), QPointF(25, 7))


class ActionEffects(QWidget):
    """Mouse-transparent layer; only its currently painted regions enter the mask."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.action = None
        self.progress = 0.0
        self.items = []

    def advance(self, action, progress: float, cat_rect) -> None:
        self.action = action
        self.progress = progress
        self.items = []
        self.setGeometry(self.parentWidget().rect())
        rect = QRectF(cat_rect)
        scale = rect.width() / 240
        if action == 'Feed' and progress < 0.60:
            t = min(progress / 0.55, 1)
            eased = t * t * (3 - 2 * t)
            size = 30 * scale * (1 - max(0, t - 0.75) / 0.25 * 0.85)
            mouth = QPointF(rect.left() + rect.width() * 0.49, rect.top() + rect.height() * 0.55)
            center = mouth + QPointF(-75 * scale * (1 - eased), 18 * scale * (1 - eased))
            opacity = min(1, (0.60 - progress) / 0.10)
            self.items.append((QRectF(center.x() - size / 2, center.y() - size / 2, size, size), opacity))
        elif action == 'Pat':
            for index in range(5):
                phase = (progress * 1.7 - index * 0.13)
                if 0 <= phase <= 1:
                    size = (15 + (index % 2) * 5) * scale
                    x = rect.center().x() + (index - 2) * 24 * scale + math.sin(phase * math.pi * 2 + index) * 8
                    y = rect.top() + rect.height() * 0.42 - phase * 100 * scale
                    self.items.append((QRectF(x - size / 2, y, size, size), math.sin(phase * math.pi)))
        elif action == 'Play':
            x = rect.center().x() + math.sin(progress * math.pi * 6) * rect.width() * 0.29
            y = rect.top() + rect.height() * 0.70
            size = 35 * scale
            self.items.append((QRectF(x - size / 2, y, size, size), 1.0))
        self.update()

    def visual_region(self) -> QRegion:
        region = QRegion()
        for rect, opacity in self.items:
            if opacity > 0.01:
                region = region.united(QRegion(rect.adjusted(-3, -3, 3, 3).toAlignedRect()))
        return region

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for rect, opacity in self.items:
            painter.save()
            painter.setOpacity(opacity)
            painter.translate(rect.topLeft())
            painter.scale(rect.width() / 32, rect.height() / 32)
            draw_effect(painter, self.action)
            painter.restore()
