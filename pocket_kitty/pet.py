"""Transparent pet window, image loading, and mouse interactions."""

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QContextMenuEvent, QCursor, QMouseEvent, QPainter, QPixmap, QRegion
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QMenu, QWidget

from pocket_kitty.radial_menu import RadialMenu
from pocket_kitty.effects import ActionEffects, AnimatedCat, SpeechBubble
from pocket_kitty.sprites import SpriteLibrary
from pocket_kitty.status import PetStatus, StatusPanel
from pocket_kitty.resize_handle import ResizeHandle
from pocket_kitty.companion import CompanionBehavior


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
        self._closing = False
        self.speech_kind = None
        self._asset_path = asset_path
        self.sprites = SpriteLibrary(asset_path)
        self.current_state = 'Idle'
        self.status = PetStatus(self)
        self.status_panel = StatusPanel(self.status, self)
        self._status_side = 'right'
        self._status_position_pending = False
        self.cat_scale = 100
        self._layout_ready = False

        self.cat_label = AnimatedCat(self)
        self.effects = ActionEffects(self)
        # Let mouse events reach the pet window, even over the image.
        self.cat_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Reserve the full radial footprint so revealing it never moves the cat.
        self.setFixedSize(320, 352)
        self._menu_active = False
        self._context_menu_open = False
        self._cat_region = QRegion()
        self._bridges = QRegion()
        self._interactive_region = QRegion()
        self.menu = RadialMenu(self)
        self.menu.progress_changed.connect(self._update_input_region)
        self.menu.hidden.connect(self._menu_hidden)
        self.menu.action_selected.connect(self.perform_action)
        self.resize_handle = ResizeHandle(self)
        self.size_opacity = QGraphicsOpacityEffect(self.resize_handle)
        self.resize_handle.setGraphicsEffect(self.size_opacity)
        self.resize_handle.hide()
        self.resize_handle.scale_requested.connect(self.set_cat_scale)
        self.resize_handle.drag_started.connect(lambda: self.hide_timer.stop())
        self.resize_handle.drag_finished.connect(self._finish_resize)
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
        self.companion = CompanionBehavior(self)
        QApplication.instance().aboutToQuit.connect(self.shutdown)

    def set_cat_image(self, path: Path) -> None:
        """Single image update point for future animation states."""
        self._asset_path = path
        maximum = QSize(round(self.IMAGE_SIZE.width() * self.cat_scale / 100), round(self.IMAGE_SIZE.height() * self.cat_scale / 100))
        state = next((key for key, value in self.sprites.paths.items() if value == path), None)
        pixmap = self.sprites.frame(state, maximum) if state else load_cat_image(path, maximum)
        size_changed = self.cat_label.size() != pixmap.size()
        self.cat_label.setPixmap(pixmap)
        self.cat_label.setFixedSize(pixmap.size())
        if size_changed or not self._layout_ready:
            self._arrange_pet()
        self._cat_region = self.cat_label.visual_region()
        self._update_input_region()

    def set_cat_scale(self, percent: int) -> None:
        if self.current_state != 'Idle':
            return
        self.cat_scale = max(50, min(125, percent))
        self.resize_handle.setToolTip(f'{self.cat_scale}% - drag to resize Kitty and menu')
        self.set_cat_image(self._asset_path)

    def _arrange_pet(self) -> None:
        old_center = self.mapToGlobal(self.menu.center.toPoint())
        cat = self.cat_label.size()
        scale = self.cat_scale / 100
        self.setFixedSize(round(320 * scale), round(352 * scale))
        self.cat_label.move(round(40 * scale), round(40 * scale))
        center = QPointF(self.width() / 2, self.cat_label.y() + cat.height() / 2)
        self.resize_handle.setGeometry(round(254 * scale), round(268 * scale), round(28 * scale), round(28 * scale))
        self.message.fit_to_text(scale)
        self.menu.arrange(self.width(), self.height(), center, scale)
        if self._layout_ready:
            self.move(old_center - center.toPoint())
            if not self.resize_handle.dragging:
                self._keep_on_screen()
        self._layout_ready = True
        self.effects.setGeometry(self.rect())
        if self.status_panel.isVisible():
            self._position_status_panel()
        if self.message.isVisible():
            self._position_speech_bubble()

    def _finish_resize(self) -> None:
        self._keep_on_screen()
        if self.status_panel.isVisible():
            self._position_status_panel()
        self._cat_region = self.cat_label.visual_region()
        self._update_input_region()
        self._sync_hover()
        self.companion.on_available()

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
            scale = self.cat_scale / 100
            top = round(32 * scale)
            corridor = max(8, round(16 * scale))
            self._bridges = QRegion(QRect(center.x() - corridor // 2, top, corridor, self.height() - 2 * top)).united(
                QRegion(QRect(top, center.y() - corridor // 2, self.width() - 2 * top, corridor))
            )
            if not self.resize_handle.isHidden():
                # A small path to the handle beside the right paw.
                foot = self.resize_handle.geometry().center()
                self._bridges = self._bridges.united(QRegion(QRect(center.x(), foot.y() - corridor // 2, foot.x() - center.x() + 1, corridor)))
            region = region.united(self._bridges)
            buttons_region = QRegion()
            for button in self.menu.buttons.values():
                buttons_region = buttons_region.united(QRegion(button.geometry(), QRegion.RegionType.Ellipse))
            if self.menu.mask() != buttons_region:
                self.menu.setMask(buttons_region)
            region = region.united(buttons_region)
        if hasattr(self, 'resize_handle') and not self.resize_handle.isHidden():
            region = region.united(QRegion(self.resize_handle.geometry()))
            self.size_opacity.setOpacity(self.menu.progress)
        region = region.united(self.effects.visual_region())
        if self._interactive_region != region:
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
        if self.resize_handle.dragging:
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
        self.resize_handle.show()
        self.resize_handle.raise_()
        self.menu.reveal(True)
        self._update_input_region()
        self.hover_timer.start()
        if self.message.isVisible():
            self._position_speech_bubble()

    def _hide_menu(self) -> None:
        self._menu_active = False
        self.menu.reveal(False)

    def _hide_if_outside(self) -> None:
        # Recheck at the deadline in case the cursor returned between polls.
        if not self.resize_handle.dragging and not self._interactive_region.contains(self.mapFromGlobal(QCursor.pos())):
            self._hide_menu()

    def _menu_hidden(self) -> None:
        self.hover_timer.stop()
        self.resize_handle.hide()
        self._update_input_region()

    def _keep_on_screen(self, desired: QPoint | None = None) -> None:
        desired = desired if desired is not None else self.pos()
        screen = QApplication.screenAt(desired + self.cat_label.geometry().center()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        if self.status_panel.isVisible() and area.width() >= self.width() + self.status_panel.width() + 12:
            reserved = self.status_panel.width() + 12
            if self._status_side == 'right':
                area.adjust(0, 0, -reserved, 0)
            else:
                area.adjust(reserved, 0, 0, 0)

        self.move(
            max(area.left(), min(desired.x(), area.right() + 1 - self.width())),
            max(area.top(), min(desired.y(), area.bottom() + 1 - self.height())),
        )
        if self.status_panel.isVisible():
            self._position_status_panel()

    def perform_action(self, action: str) -> bool:
        if action == 'Status':
            if self.status_panel.isVisible():
                self.status_panel.close()
            else:
                screen = QApplication.screenAt(self.mapToGlobal(self.cat_label.geometry().center())) or QApplication.primaryScreen()
                if screen:
                    area = screen.availableGeometry()
                    left = self.x() - area.left()
                    right = area.right() + 1 - self.x() - self.width()
                    self._status_side = 'right' if right >= left else 'left'
                self.status_panel.show()
                self._keep_on_screen()
                self._position_status_panel()
                self.status_panel.raise_()
            return True
        if self.current_state != 'Idle' or action not in self.ACTIONS:
            return False
        duration, text = self.ACTIONS[action]
        self.companion.action_started()
        self.cat_label.begin_action()
        self.current_state = action
        self.cat_label.action = action
        self.cat_label.progress = 0.0
        self.set_cat_image(self.sprites.paths[action])
        self.status.apply(action)
        for name, button in self.menu.buttons.items():
            button.setEnabled(name == 'Status')
        self.resize_handle.setEnabled(False)
        self.show_speech(text, 'action')
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
        self.cat_label.idle_pixmap = None
        self.cat_label.idle_region = QRegion()
        self.effects.advance(None, 0.0, self.cat_label.geometry())
        self.hide_speech()
        self.set_cat_image(self.sprites.paths['Idle'])
        for button in self.menu.buttons.values():
            button.setEnabled(True)
        self.resize_handle.setEnabled(True)
        self._update_input_region()
        self.companion.on_available()

    def show_speech(self, text: str, kind: str) -> None:
        self.speech_kind = kind
        self.message.setText(text)
        self.message.fit_to_text(self.cat_scale / 100)
        self._position_speech_bubble()
        self.message.reveal()
        self.message.raise_()

    def hide_speech(self, animated=False) -> None:
        self.speech_kind = None
        self.message.dismiss(animated)

    def _position_status_panel(self) -> None:
        # Position only the panel here. Moving the pet from its own moveEvent
        # can cause a native move/resize feedback loop on Windows.
        self._status_position_pending = False
        if self._closing or not self.status_panel.isVisible() or self.resize_handle.dragging:
            return
        screen = QApplication.screenAt(self.mapToGlobal(self.cat_label.geometry().center())) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        gap = 12
        width = self.status_panel.width()
        x = self.x() + self.width() + gap if self._status_side == 'right' else self.x() - width - gap
        x = max(area.left(), min(x, area.right() + 1 - width))
        y = max(area.top(), min(self.y() + self.cat_label.y(), area.bottom() + 1 - self.status_panel.height()))
        position = QPoint(x, y)
        if self.status_panel.pos() != position:
            self.status_panel.move(position)
        if self.message.isVisible():
            self._position_speech_bubble()

    def _position_speech_bubble(self) -> None:
        if self._closing:
            return
        screen = QApplication.screenAt(self.mapToGlobal(self.cat_label.geometry().center())) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        cat = QRect(self.mapToGlobal(self.cat_label.pos()), self.cat_label.size())
        width, height = self.message.width(), self.message.height()
        gap = round(46 * self.cat_scale / 100)
        y = max(area.top(), cat.top() - height - 8)
        obstacles = [QRect(self.menu.mapToGlobal(button.pos()), button.size())
                     for button in self.menu.buttons.values()] if not self.menu.isHidden() else []
        if self.status_panel.isVisible():
            obstacles.append(self.status_panel.geometry())
        candidates = [(cat.center().x() - width - gap, 'right'), (cat.center().x() + gap, 'left')]
        # Side positions are useful when the monitor's top edge leaves too
        # little headroom. Keep bubbles clear of the entire image frame.
        candidates.extend([(cat.left() - width - 12, 'right'), (cat.right() + 12, 'left'),
                           (self.x() - width - 12, 'right'), (self.x() + self.width() + 12, 'left')])
        if self.status_panel.isVisible():
            panel = self.status_panel.geometry()
            candidates.extend([(panel.right() + 12, 'left'), (panel.left() - width - 12, 'right')])
        # Prefer upper-left; flip to upper-right near the left screen edge.
        for x, tail in candidates:
            rect = QRect(x, y, width, height)
            if area.contains(rect) and not rect.intersects(cat) and not any(rect.intersects(item) for item in obstacles):
                self.message.tail_side = tail
                self.message.tail_above = False
                self.message.move(rect.topLeft())
                self.message.update()
                return
        # At tight top corners a status panel can occupy the only free side.
        # Search clear space above/below the group before using a clamped fallback.
        rows = [self.y() - height - 8, self.y() + self.height() + 8]
        if self.status_panel.isVisible():
            rows.extend([panel.top() - height - 8, panel.bottom() + 12])
        columns = [x for x, _ in candidates] + [area.left(), area.right() + 1 - width]
        for row in rows:
            for column in columns:
                rect = QRect(column, row, width, height)
                if area.contains(rect) and not rect.intersects(cat) and not any(rect.intersects(item) for item in obstacles):
                    self.message.tail_side = 'right' if rect.center().x() < cat.center().x() else 'left'
                    self.message.tail_above = rect.center().y() > cat.center().y()
                    self.message.move(rect.topLeft())
                    self.message.update()
                    return
        x = max(area.left(), min(candidates[0][0], area.right() + 1 - width))
        self.message.tail_side = 'right'
        self.message.tail_above = False
        self.message.move(x, max(area.top(), self.y() - height - 8))
        self.message.update()

    def moveEvent(self, event) -> None:
        if hasattr(self, 'status_panel') and self.status_panel.isVisible() and not self._status_position_pending:
            self._status_position_pending = True
            QTimer.singleShot(0, self._position_status_panel)
        if hasattr(self, 'message') and self.message.isVisible():
            self._position_speech_bubble()
        super().moveEvent(event)

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.companion.stop()
        self.hide_timer.stop()
        self.hover_timer.stop()
        self.action_animation.stop()
        self.menu.animation.stop()
        for button in self.menu.buttons.values():
            button._hover_animation.stop()
        self.hide_speech()
        self.status_panel.close()

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
            self.companion.on_available()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def create_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet(
            'QMenu { background: #fff8f5; color: #58475f; border: 1px solid #e5d2e1; padding: 5px; }'
            'QMenu::item { padding: 7px 18px; border-radius: 6px; }'
            'QMenu::item:selected { background: #f6dfeb; }'
        )
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)
        menu.addSeparator()
        demo_action = menu.addAction('Demo Mode')
        demo_action.setCheckable(True)
        demo_action.setChecked(self.companion.demo_mode)
        demo_action.toggled.connect(self.companion.set_demo_mode)
        return menu

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._context_menu_open = True
        self.hide_timer.stop()
        menu = self.create_context_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()
        self._context_menu_open = False
        self._sync_hover()
        self.companion.on_available()
        event.accept()
