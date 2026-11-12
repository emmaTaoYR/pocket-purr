"""Transparent pet window, image loading, and mouse interactions."""

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QContextMenuEvent, QCursor, QMouseEvent, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QMenu, QSlider, QWidget

from pocket_kitty.radial_menu import RadialMenu
from pocket_kitty.effects import ActionEffects, AnimatedCat, SpeechBubble
from pocket_kitty.sprites import SpriteLibrary
from pocket_kitty.status import PetStatus, StatusPanel


def load_cat_image(path: Path, maximum_size: QSize) -> QPixmap:
    """Load a PNG without changing its alpha channel or aspect ratio."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Cat image is missing:\n{path}\n\n"
            "Place your transparent cat PNG at assets/cat_idle.png, then restart."
        )
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        raise ValueError(f"Cannot read the cat image:\n{path}\n\nUse a valid PNG file.")
    return pixmap.scaled(
        maximum_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class PetWindow(QWidget):
    """A small desktop overlay. Future pet controls can be child widgets."""

    IMAGE_SIZE = QSize(240, 260)
    DESKTOP_MARGIN = 24
    ACTIONS = {
        'Feed': (2000, 'Yummy! \U0001f41f'),
        'Pat': (2000, 'Prrrr... \U0001f497'),
        'Play': (3000, "Let's play! \U0001fab6"),
    }

    def __init__(self, asset_path: Path) -> None:
        super().__init__()
        self.setWindowTitle("Pocket Kitty")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._drag_offset: QPoint | None = None
        self._asset_path = asset_path
        self.sprites = SpriteLibrary(asset_path)
        self.current_state = 'Idle'
        self.status = PetStatus(self)
        self.status_panel = StatusPanel(self.status, self)
        self._placing_status = False
        self.cat_scale = 100
        self._layout_ready = False

        self.cat_label = AnimatedCat(self)
        self.effects = ActionEffects(self)
        # Let mouse events reach the pet window, even over the image.
        self.cat_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Reserve the full radial footprint so revealing it never moves the cat.
        self.setFixedSize(440, 472)
        self._menu_active = False
        self._context_menu_open = False
        self._cat_region = QRegion()
        self._bridges = QRegion()
        self._interactive_region = QRegion()
        self.menu = RadialMenu(self)
        self.menu.progress_changed.connect(self._update_input_region)
        self.menu.hidden.connect(self._menu_hidden)
        self.menu.action_selected.connect(self.perform_action)
        self.size_control = QWidget(self)
        self.size_control.setCursor(Qt.CursorShape.ArrowCursor)
        self.size_control.setStyleSheet(
            'QWidget { background: #fff5ef; color: #58475f; border-radius: 14px; }'
            'QLabel { font: 9pt "Segoe UI"; }'
            'QSlider::groove:horizontal { height: 5px; background: #e5d6e9; border-radius: 2px; }'
            'QSlider::handle:horizontal { width: 13px; margin: -5px 0; background: #c29abb; border-radius: 6px; }'
            'QSlider::sub-page:horizontal { background: #d4aecb; border-radius: 2px; }'
        )
        size_layout = QHBoxLayout(self.size_control)
        size_layout.setContentsMargins(10, 3, 10, 3)
        size_layout.setSpacing(7)
        size_layout.addWidget(QLabel('Size', self.size_control))
        self.size_slider = QSlider(Qt.Orientation.Horizontal, self.size_control)
        self.size_slider.setRange(50, 125)
        self.size_slider.setValue(100)
        self.size_slider.setAccessibleName('Cat size')
        self.size_slider.setToolTip('Cat size: 50% - 125%')
        size_layout.addWidget(self.size_slider, 1)
        self.size_value = QLabel('100%', self.size_control)
        self.size_value.setFixedWidth(34)
        size_layout.addWidget(self.size_value)
        self.size_opacity = QGraphicsOpacityEffect(self.size_control)
        self.size_control.setGraphicsEffect(self.size_opacity)
        self.size_control.hide()
        self.size_slider.valueChanged.connect(self.set_cat_scale)
        self.size_slider.sliderPressed.connect(lambda: self.hide_timer.stop())
        self.size_slider.sliderReleased.connect(self._finish_resize)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(300)
        self.hide_timer.timeout.connect(self._hide_if_outside)
        # Poll the actual pointer so transitions between child buttons and gaps
        # share one hover area instead of relying on individual leave events.
        self.hover_timer = QTimer(self)
        self.hover_timer.setInterval(40)
        self.hover_timer.timeout.connect(self._sync_hover)
        self.message = SpeechBubble(self)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setGeometry(101, 326, 238, 34)
        self.message.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.message.hide()
        self.action_animation = QVariantAnimation(self)
        self.action_animation.setStartValue(0.0)
        self.action_animation.setEndValue(1.0)
        self.action_animation.valueChanged.connect(self._advance_action)
        self.action_animation.finished.connect(self._finish_action)
        self.set_cat_image(asset_path)
        self.position_at_startup()

    def set_cat_image(self, path: Path) -> None:
        """Single image update point for future animation states."""
        self._asset_path = path
        maximum = QSize(round(self.IMAGE_SIZE.width() * self.cat_scale / 100), round(self.IMAGE_SIZE.height() * self.cat_scale / 100))
        state = next((key for key, value in self.sprites.paths.items() if value == path), None)
        pixmap = self.sprites.frame(state, maximum) if state else load_cat_image(path, maximum)
        size_changed = self.cat_label.size() != pixmap.size()
        self.cat_label.setPixmap(pixmap)
        self.cat_label.setFixedSize(pixmap.size())
        if not self.size_slider.isSliderDown() and (size_changed or not self._layout_ready):
            self._arrange_pet()
        elif self.size_slider.isSliderDown():
            # Keep the slider under the pointer throughout a drag. Reflow the
            # surrounding menu on release; the image itself previews live.
            center = self.menu.center.toPoint()
            self.cat_label.move(center.x() - pixmap.width() // 2, center.y() - pixmap.height() // 2)
        self._cat_region = self.cat_label.visual_region()
        self._update_input_region()

    def set_cat_scale(self, percent: int) -> None:
        self.cat_scale = max(50, min(125, percent))
        self.size_value.setText(f'{self.cat_scale}%')
        if self.size_slider.value() != self.cat_scale:
            self.size_slider.setValue(self.cat_scale)
            return
        self.set_cat_image(self._asset_path)

    def _arrange_pet(self) -> None:
        old_center = self.mapToGlobal(self.menu.center.toPoint())
        cat = self.cat_label.size()
        self.setFixedSize(cat.width() + 200, cat.height() + 300)
        center = QPointF(self.width() / 2, 106 + cat.height() / 2)
        self.cat_label.move(100, 106)
        self.size_control.setGeometry(self.width() // 2 - 95, cat.height() + 158, 190, 34)
        self.message.setGeometry(self.width() // 2 - 119, cat.height() + 110, 238, 38)
        self.menu.arrange(self.width(), self.height(), center)
        if self._layout_ready:
            self.move(old_center - center.toPoint())
            self._keep_on_screen()
        self._layout_ready = True
        self.effects.setGeometry(self.rect())
        if self.status_panel.isVisible():
            self._position_status_panel()

    def _finish_resize(self) -> None:
        self._arrange_pet()
        self._cat_region = QRegion(self.cat_label.pixmap().mask()).translated(self.cat_label.pos())
        self._update_input_region()
        self._sync_hover()

    def position_at_startup(self) -> None:
        """Use the primary monitor's work area, leaving room for the taskbar."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            max(area.left(), area.right() + 1 - self.width() - self.DESKTOP_MARGIN),
            max(area.top(), area.bottom() + 1 - self.height() - self.DESKTOP_MARGIN),
        )

    def _update_input_region(self) -> None:
        region = QRegion(self._cat_region)
        self._bridges = QRegion()
        if not self.menu.isHidden():
            # Only narrow travel corridors catch input; unused desktop corners
            # stay outside the native window mask and remain click-through.
            center = self.menu.center.toPoint()
            self._bridges = QRegion(QRect(center.x() - 10, 50, 20, self.height() - 100)).united(
                QRegion(QRect(50, center.y() - 10, self.width() - 100, 20))
            )
            region = region.united(self._bridges)
            buttons_region = QRegion()
            for button in self.menu.buttons.values():
                buttons_region = buttons_region.united(QRegion(button.geometry(), QRegion.RegionType.Ellipse))
            self.menu.setMask(buttons_region)
            region = region.united(buttons_region)
        if hasattr(self, 'size_control') and not self.size_control.isHidden():
            region = region.united(QRegion(self.size_control.geometry()))
            self.size_opacity.setOpacity(self.menu.progress)
        if hasattr(self, 'message') and not self.message.isHidden():
            region = region.united(QRegion(self.message.geometry()))
        region = region.united(self.effects.visual_region())
        self._interactive_region = region
        self.setMask(region)
        self.update()

    def paintEvent(self, event) -> None:
        # Windows layered windows hit-test nonzero alpha. These nearly invisible
        # corridors let the pointer cross the gap without stealing a large box.
        painter = QPainter(self)
        painter.setClipRegion(self._bridges)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

    def enterEvent(self, event) -> None:
        self._sync_hover()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._sync_hover()
        super().leaveEvent(event)

    def _sync_hover(self) -> None:
        if self._drag_offset is not None or self._context_menu_open:
            return
        if self.size_slider.isSliderDown():
            self.hide_timer.stop()
            return
        point = self.mapFromGlobal(QCursor.pos())
        inside = self._interactive_region.contains(point)
        if inside:
            self.hide_timer.stop()
            if not self._menu_active and (self._cat_region.contains(point) or not self.menu.isHidden()):
                self._show_menu()
        elif self._menu_active and not self.hide_timer.isActive():
            self.hide_timer.start()

    def _show_menu(self) -> None:
        self._keep_on_screen()
        self._menu_active = True
        self.menu.setEnabled(True)
        self.size_control.show()
        self.size_control.raise_()
        self.menu.reveal(True)
        self._update_input_region()
        self.hover_timer.start()

    def _hide_menu(self) -> None:
        self._menu_active = False
        self.menu.reveal(False)

    def _hide_if_outside(self) -> None:
        # Recheck at the deadline in case the cursor returned between polls.
        if not self.size_slider.isSliderDown() and not self._interactive_region.contains(self.mapFromGlobal(QCursor.pos())):
            self._hide_menu()

    def _menu_hidden(self) -> None:
        self.hover_timer.stop()
        self.size_control.hide()
        self._update_input_region()

    def _keep_on_screen(self, desired: QPoint | None = None) -> None:
        desired = desired if desired is not None else self.pos()
        screen = QApplication.screenAt(desired + self.cat_label.geometry().center()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        self.move(
            max(area.left(), min(desired.x(), area.right() + 1 - self.width())),
            max(area.top(), min(desired.y(), area.bottom() + 1 - self.height())),
        )

    def perform_action(self, action: str) -> bool:
        if action == 'Status':
            self.status_panel.show()
            self._position_status_panel()
            self.status_panel.raise_()
            return True
        if self.current_state != 'Idle' or action not in self.ACTIONS:
            return False
        duration, text = self.ACTIONS[action]
        self.current_state = action
        self.cat_label.action = action
        self.cat_label.progress = 0.0
        self.set_cat_image(self.sprites.paths[action])
        self.status.apply(action)
        for name, button in self.menu.buttons.items():
            button.setEnabled(name == 'Status')
        self.size_control.setEnabled(False)
        self.message.setText(text)
        self.message.show()
        self.message.raise_()
        self.action_animation.setDuration(duration)
        self._advance_action(0.0)
        self.action_animation.start()
        return True

    def _advance_action(self, progress: float) -> None:
        if self.current_state == 'Idle':
            return
        self.cat_label.progress = progress
        self.cat_label.update()
        self.effects.advance(self.current_state, progress, self.cat_label.geometry())
        self._cat_region = self.cat_label.visual_region()
        self._update_input_region()

    def _finish_action(self) -> None:
        self.current_state = 'Idle'
        self.cat_label.action = None
        self.cat_label.progress = 0.0
        self.effects.advance(None, 0.0, self.cat_label.geometry())
        self.message.hide()
        self.set_cat_image(self.sprites.paths['Idle'])
        for button in self.menu.buttons.values():
            button.setEnabled(True)
        self.size_control.setEnabled(True)
        self._update_input_region()

    def _position_status_panel(self) -> None:
        if self._placing_status:
            return
        screen = QApplication.screenAt(self.mapToGlobal(self.cat_label.geometry().center())) or QApplication.primaryScreen()
        if screen is None:
            return
        self._placing_status = True
        try:
            area = screen.availableGeometry().adjusted(8, 8, -8, -8)
            gap = 12
            width = self.status_panel.width()
            left_space = self.x() - area.left()
            right_space = area.right() + 1 - self.x() - self.width()
            on_right = right_space >= width + gap or right_space >= left_space
            if max(left_space, right_space) < width + gap and area.width() >= self.width() + width + gap:
                # Make room beside the whole radial footprint, not on the cat.
                x = area.right() + 1 - self.width() - width - gap if on_right else area.left() + width + gap
                self.move(x, self.y())
            x = self.x() + self.width() + gap if on_right else self.x() - width - gap
            x = max(area.left(), min(x, area.right() + 1 - width))
            y = max(area.top(), min(self.y() + self.cat_label.y(), area.bottom() + 1 - self.status_panel.height()))
            self.status_panel.move(x, y)
        finally:
            self._placing_status = False

    def moveEvent(self, event) -> None:
        if hasattr(self, 'status_panel') and self.status_panel.isVisible():
            self._position_status_panel()
        super().moveEvent(event)

    def closeEvent(self, event) -> None:
        self.action_animation.stop()
        self.status_panel.close()
        super().closeEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._cat_region.contains(event.position().toPoint()):
            self.hide_timer.stop()
            self.menu.setEnabled(False)
            self._hide_menu()
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self._keep_on_screen(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._sync_hover()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Keep menu creation separate so more actions can be added later."""
        self._context_menu_open = True
        self.hide_timer.stop()
        menu = QMenu(self)
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)
        menu.exec(event.globalPos())
        menu.deleteLater()
        self._context_menu_open = False
        self._sync_hover()
        event.accept()
