"""Small local Qt drawings and transforms driven by one action timeline."""

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRect, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QRegion, QTransform
from PySide6.QtWidgets import QLabel, QWidget


class AnimatedCat(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.action = None
        self.progress = 0.0
        self.base_region = QRegion()
        self.idle_seconds = 0.0
        self.float_amount = 0.0
        self.idle_pixmap = None
        self.idle_region = QRegion()

    def begin_action(self):
        self.idle_pixmap = self.pixmap()
        self.idle_region = QRegion(self.base_region)

    def action_blend(self):
        if self.action is None:
            return 0.0
        def ease(value):
            value = max(0.0, min(1.0, value))
            return value * value * (3 - 2 * value)
        return ease(self.progress / 0.1) * ease((1 - self.progress) / 0.1)

    def setPixmap(self, pixmap):
        super().setPixmap(pixmap)
        self.base_region = QRegion(pixmap.mask())

    def frame_transform(self) -> QTransform:
        transform = QTransform()
        blend = self.action_blend()
        breath = math.sin(self.idle_seconds * math.pi * 2 / 5.5) * (1 - blend)
        transform.translate(self.width() / 2, self.height() * 0.92)
        transform.translate(0, -1.6 * self.float_amount * (self.width() / 240) * (1 - blend))
        transform.scale(1 + 0.0015 * breath, 1 + 0.0035 * breath)
        wave = math.sin(self.progress * math.pi * 6)
        if self.action == 'Feed':
            chew = math.sin(max(0, self.progress - 0.45) * math.pi * 14) * blend
            transform.translate(0, -abs(chew) * 2)
            transform.scale(1 + chew * 0.012, 1 - chew * 0.012)
        elif self.action == 'Pat':
            bounce = wave ** 2 * blend
            transform.translate(0, -bounce * 4)
            transform.scale(1 + bounce * 0.018, 1 - bounce * 0.018)
        elif self.action == 'Play':
            transform.translate(wave * 3 * blend, 0)
            transform.rotate(wave * 2.3 * blend)
        transform.translate(-self.width() / 2, -self.height() * 0.92)
        return transform

    def visual_region(self) -> QRegion:
        region = self.base_region
        if self.action is not None:
            region = region.united(self.idle_region)
        return self.frame_transform().map(region).translated(self.pos())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setTransform(self.frame_transform())
        pixmap = self.pixmap()
        if pixmap and not pixmap.isNull():
            if self.action is not None and self.idle_pixmap is not None:
                blend = self.action_blend()
                painter.setOpacity(1 - blend)
                painter.drawPixmap(0, 0, self.idle_pixmap)
                painter.setOpacity(blend)
            painter.drawPixmap(0, 0, pixmap)


class SpeechBubble(QLabel):
    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.tail_side = 'right'
        self.tail_above = False
        self.opacity = 1.0
        self.fade = QVariantAnimation(self)
        self.fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade.valueChanged.connect(self._set_opacity)
        self.fade.finished.connect(self._fade_finished)

    def fit_to_text(self, scale=1.0):
        self.setFont(QFont('Segoe UI', max(9, min(11, round(10 * scale)))))
        metrics = QFontMetrics(self.font())
        maximum = max(210, min(280, round(240 * scale)))
        width = min(maximum, max(160, metrics.horizontalAdvance(self.text()) + 32))
        bounds = metrics.boundingRect(QRect(0, 0, width - 28, 1000),
                                      Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.text())
        self.setFixedSize(width, max(46, bounds.height() + 28))

    def _set_opacity(self, value):
        self.opacity = value
        self.update()

    def reveal(self):
        was_hidden = self.isHidden()
        self.fade.stop()
        if was_hidden:
            self.opacity = 0.0
        self.show()
        self.fade.setDuration(160)
        self.fade.setStartValue(self.opacity)
        self.fade.setEndValue(1.0)
        self.fade.start()

    def dismiss(self, animated=False):
        self.fade.stop()
        if not animated:
            self.hide()
            return
        self.fade.setDuration(160)
        self.fade.setStartValue(self.opacity)
        self.fade.setEndValue(0.0)
        self.fade.start()

    def _fade_finished(self):
        if self.opacity == 0:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.opacity)
        path = QPainterPath()
        path.addRoundedRect(QRectF(4, 13 if self.tail_above else 3, self.width() - 8, self.height() - 18), 14, 14)
        x = self.width() - 30 if self.tail_side == 'right' else 30
        tip = x + 16 if self.tail_side == 'right' else x - 16
        base_y = 16 if self.tail_above else self.height() - 17
        tip_y = 4 if self.tail_above else self.height() - 5
        tail = QPainterPath(QPointF(x - 8, base_y))
        tail.lineTo(tip, tip_y)
        tail.lineTo(x + 8, base_y)
        tail.closeSubpath()
        path = path.united(tail)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(80, 55, 80, 17))
        painter.drawPath(path.translated(0, 3))
        painter.setPen(QPen(QColor('#e9d7dc'), 0.8))
        painter.setBrush(QColor('#fff7ee'))
        painter.drawPath(path)
        painter.setPen(QColor('#58475f'))
        painter.setFont(self.font())
        painter.drawText(QRectF(14, 15 if self.tail_above else 5, self.width() - 28, self.height() - 24),
                         Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.text())


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
