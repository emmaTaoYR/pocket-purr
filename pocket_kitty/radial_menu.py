"""Small painted Qt buttons: no icon packs, image generation, or web UI."""

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QAbstractButton, QWidget


class RadialButton(QAbstractButton):
    """A circular hit target with a hand-painted icon and soft shadow."""

    def __init__(self, name: str, color: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setText(name)
        self.setAccessibleName(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.color = QColor(color)
        self.reveal = 0.0
        self.hover = 0.0
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.setDuration(130)
        self._hover_animation.valueChanged.connect(self._set_hover)

    def _set_hover(self, value: float) -> None:
        self.hover = value
        self.update()

    def _animate_hover(self, value: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self.hover)
        self._hover_animation.setEndValue(value)
        self._hover_animation.start()

    def enterEvent(self, event) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def hitButton(self, position) -> bool:
        center = QPointF(self.width() / 2, self.height() / 2)
        delta = QPointF(position) - center
        return delta.x() ** 2 + delta.y() ** 2 <= (self.width() * 0.43) ** 2

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.reveal * (1.0 if self.isEnabled() else 0.48))
        painter.scale(self.width() / 100, self.height() / 100)
        painter.translate(50, 50)
        scale = 0.92 + 0.08 * self.reveal + 0.025 * self.hover
        painter.scale(scale, scale)
        painter.translate(-50, -50 - self.hover)
        painter.setPen(Qt.PenStyle.NoPen)
        for spread in range(6, 0, -1):
            painter.setBrush(QColor(70, 45, 70, 4))
            painter.drawEllipse(QRectF(8 - spread / 2, 12 - spread / 2, 84 + spread, 84 + spread))
        fill = self.color.lighter(round(100 + 7 * self.hover))
        if self.isDown():
            fill = self.color.darker(106)
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(255, 255, 255, 225), 1.5))
        painter.drawEllipse(QRectF(8, 8, 84, 84))
        if self.hasFocus() and self.window().testAttribute(Qt.WidgetAttribute.WA_KeyboardFocusChange):
            painter.setPen(QPen(QColor('#977da8'), 1.5, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(12, 12, 76, 76))
        painter.save()
        painter.translate(34, 23)
        self._paint_icon(painter)
        painter.restore()
        painter.setPen(QColor('#58475f'))
        painter.setFont(QFont('Segoe UI', 15, QFont.Weight.DemiBold))
        painter.drawText(QRectF(8, 60, 84, 23), Qt.AlignmentFlag.AlignCenter, self.text())

    def _paint_icon(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor('#89718f'), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        if self.text() == 'Feed':
            painter.setBrush(QColor('#8fcbe4'))
            path.moveTo(8, 16)
            path.lineTo(1, 8)
            path.lineTo(1, 24)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawEllipse(QRectF(7, 6, 25, 20))
            painter.setBrush(QColor('#58475f'))
            painter.drawEllipse(QRectF(25, 12, 2, 2))
        elif self.text() == 'Pat':
            painter.setBrush(QColor('#f397b4'))
            path.moveTo(16, 29)
            path.cubicTo(-12, 12, 6, -3, 16, 8)
            path.cubicTo(26, -3, 44, 12, 16, 29)
            painter.drawPath(path)
        elif self.text() == 'Play':
            painter.setBrush(QColor('#f0b793'))
            path.moveTo(5, 27)
            path.cubicTo(0, 6, 16, 0, 30, 2)
            path.cubicTo(32, 17, 23, 28, 5, 27)
            painter.drawPath(path)
            painter.drawLine(QPointF(1, 32), QPointF(24, 8))
            painter.drawLine(QPointF(12, 20), QPointF(23, 19))
        else:
            painter.setBrush(QColor('#edbf61'))
            for x, y, radius in [(17, 16, 13), (3, 5, 4), (30, 28, 4)]:
                star = QPainterPath(QPointF(x, y - radius))
                star.lineTo(x + radius * 0.3, y - radius * 0.3)
                star.lineTo(x + radius, y)
                star.lineTo(x + radius * 0.3, y + radius * 0.3)
                star.lineTo(x, y + radius)
                star.lineTo(x - radius * 0.3, y + radius * 0.3)
                star.lineTo(x - radius, y)
                star.lineTo(x - radius * 0.3, y - radius * 0.3)
                star.closeSubpath()
                painter.drawPath(star)


class RadialMenu(QWidget):
    """Four action controls with a reversible fade and outward scale animation."""

    action_selected = Signal(str)
    progress_changed = Signal()
    hidden = Signal()
    CENTERS = {'Feed': (160, 32), 'Pat': (32, 169), 'Play': (288, 169), 'Status': (160, 320)}

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setGeometry(0, 0, 320, 352)
        self.progress = 0.0
        self.button_size = 64
        self.center = QPointF(160, 169)
        self.centers = dict(self.CENTERS)
        self.buttons = {}
        colors = ['#daedf8', '#fbe0eb', '#fce5d8', '#fff0ca']
        for (name, _), color in zip(self.CENTERS.items(), colors):
            button = RadialButton(name, color, self)
            button.clicked.connect(lambda checked=False, action=name: self.action_selected.emit(action))
            self.buttons[name] = button
        self.animation = QVariantAnimation(self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self._set_progress)
        self.animation.finished.connect(self._finished)
        self._set_progress(0.0)
        self.hide()

    def arrange(self, width: int, height: int, center: QPointF, scale: float = 1.0) -> None:
        """Keep the same four directions when the user resizes the cat."""
        self.setGeometry(0, 0, width, height)
        self.center = center
        self.button_size = round(64 * scale)
        self.centers = {
            'Feed': (center.x(), 32 * scale),
            'Pat': (32 * scale, center.y()),
            'Play': (width - 32 * scale, center.y()),
            'Status': (center.x(), height - 32 * scale),
        }
        self._set_progress(self.progress)

    def _set_progress(self, value: float) -> None:
        self.progress = value
        for name, button in self.buttons.items():
            x, y = self.centers[name]
            expansion = 0.94 + 0.06 * value
            half = self.button_size / 2
            button.setGeometry(round(self.center.x() + (x - self.center.x()) * expansion - half), round(self.center.y() + (y - self.center.y()) * expansion - half), self.button_size, self.button_size)
            button.reveal = value
            button.update()
        self.progress_changed.emit()

    def reveal(self, visible: bool) -> None:
        self.animation.stop()
        if visible:
            self.show()
        self.animation.setDuration(180 if visible else 150)
        self.animation.setStartValue(self.progress)
        self.animation.setEndValue(1.0 if visible else 0.0)
        self.animation.start()

    def _finished(self) -> None:
        if self.progress == 0.0:
            self.hide()
            self.hidden.emit()
