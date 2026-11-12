"""Interaction regressions; run with python -m unittest discover -s tests -v."""

import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from pathlib import Path
import tempfile
import shutil
import unittest

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent, QCursor, QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from pocket_kitty.pet import PetWindow, load_cat_image
from pocket_kitty.sprites import SpriteLibrary


class PetInteractions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        QCursor.setPos(0, 0)
        self.pet = PetWindow(Path(__file__).resolve().parents[1] / 'assets/cat_idle.png')
        self.pet.show()
        self.app.processEvents()

    def tearDown(self):
        self.pet.hide_timer.stop()
        self.pet.hover_timer.stop()
        self.pet.action_animation.stop()
        self.pet.close()
        self.pet.deleteLater()
        self.app.processEvents()

    def point_at(self, local):
        QCursor.setPos(self.pet.mapToGlobal(local))
        self.pet._sync_hover()

    def open_menu(self):
        self.point_at(self.pet.cat_label.geometry().center())
        self.wait_for_menu()
        self.assertTrue(self.pet._menu_active)
        self.assertAlmostEqual(self.pet.menu.progress, 1.0)

    def wait_for_menu(self):
        for _ in range(50):
            if self.pet.menu.progress == 1.0:
                return
            QTest.qWait(20)
        self.fail('The hover menu did not finish opening within one second')

    def test_window_and_asset_preserved(self):
        self.assertTrue(self.pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(self.pet.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(self.pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        image = self.pet.cat_label.pixmap().toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertAlmostEqual(image.width() / image.height(), 1208 / 1302, places=2)
        with self.assertRaisesRegex(FileNotFoundError, 'assets/cat_idle.png'):
            load_cat_image(Path('does-not-exist/cat_idle.png'), self.pet.IMAGE_SIZE)

    def test_hover_reveal_and_delayed_hide(self):
        self.open_menu()
        self.point_at(QPoint(-20, -20))
        QTest.qWait(180)
        self.assertTrue(self.pet._menu_active)
        QTest.qWait(350)
        self.assertTrue(self.pet.menu.isHidden())
        self.assertFalse(self.pet._menu_active)

    def test_all_routes_stay_open_and_buttons_click(self):
        self.open_menu()
        for name, button in self.pet.menu.buttons.items():
            center = button.geometry().center()
            cat_center = self.pet.cat_label.geometry().center()
            # Slow travel exceeds the hide delay, catching gap flicker regressions.
            for step in range(1, 5):
                point = cat_center + (center - cat_center) * (step / 4)
                self.point_at(point)
                QTest.qWait(100)
                self.assertTrue(self.pet._menu_active, name)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=button.rect().center())
            self.assert_action_response(name)
            self.assertIsNone(self.pet._drag_offset)
            self.point_at(cat_center)

    def test_return_during_delay_and_fade(self):
        self.open_menu()
        self.point_at(QPoint(-20, -20))
        QTest.qWait(150)
        self.point_at(self.pet.menu.buttons['Feed'].geometry().center())
        QTest.qWait(350)
        self.assertTrue(self.pet._menu_active)
        self.point_at(QPoint(-20, -20))
        QTest.qWait(340)
        self.point_at(self.pet.cat_label.geometry().center())
        self.wait_for_menu()
        self.assertAlmostEqual(self.pet.menu.progress, 1.0)

    def test_transparent_corners_and_menu_clamping(self):
        self.assertFalse(self.pet.mask().contains(QPoint(5, 5)))
        self.assertFalse(self.pet.mask().contains(QPoint(220, 50)))
        area = self.app.primaryScreen().availableGeometry()
        for corner in [area.topLeft(), area.topRight(), area.bottomLeft(), area.bottomRight()]:
            self.pet.move(corner)
            self.pet._show_menu()
            QTest.qWait(200)
            self.assertTrue(area.contains(self.pet.geometry()))
            for button in self.pet.menu.buttons.values():
                self.assertTrue(area.contains(button.mapToGlobal(button.rect().topLeft())))
                self.assertTrue(area.contains(button.mapToGlobal(button.rect().bottomRight())))
            self.assertFalse(self.pet.mask().contains(QPoint(5, 5)))

    def test_cat_drag_still_works(self):
        area = self.app.primaryScreen().availableGeometry()
        self.pet.move(area.topLeft() + QPoint(20, 20))
        start = self.pet.pos()
        local = self.pet.cat_label.geometry().center()
        self.point_at(local)
        QTest.mousePress(self.pet, Qt.MouseButton.LeftButton, pos=local)
        self.assertIsNotNone(self.pet._drag_offset)
        movement = QMouseEvent(QEvent.Type.MouseMove, QPointF(local), QPointF(start + local + QPoint(30, 20)), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.pet, movement)
        self.assertEqual(self.pet.pos(), start + QPoint(30, 20))
        QTest.mouseRelease(self.pet, Qt.MouseButton.LeftButton, pos=local)
        self.assertIsNone(self.pet._drag_offset)

    def assert_action_response(self, name):
        if name == 'Status':
            self.assertTrue(self.pet.status_panel.isVisible())
            QTest.mouseClick(self.pet.status_panel.close_button, Qt.MouseButton.LeftButton)
            self.assertFalse(self.pet.status_panel.isVisible())
        else:
            self.assertEqual(self.pet.current_state, name)
            self.assertEqual(self.pet.message.text(), self.pet.ACTIONS[name][1])
            self.assertTrue(self.pet.message.isVisible())
            self.pet.action_animation.setCurrentTime(self.pet.action_animation.duration())
            self.assertEqual(self.pet.current_state, 'Idle')

    def test_resize_preserves_aspect_ratio_and_menu_bounds(self):
        self.open_menu()
        for percent in (50, 125, 100):
            self.pet.set_cat_scale(percent)
            self.assertEqual(self.pet.cat_scale, percent)
            self.assertIn(f'{percent}%', self.pet.resize_handle.toolTip())
            image = self.pet.cat_label.pixmap()
            self.assertAlmostEqual(image.width() / image.height(), 1208 / 1302, places=2)
            self.assertEqual(image.width(), round(240 * percent / 100))
            self.assertTrue(self.pet.mask().contains(self.pet.resize_handle.geometry().center()))
            self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.pet.geometry()))
            for button in self.pet.menu.buttons.values():
                self.assertTrue(self.pet.rect().contains(button.geometry()))
                QTest.mouseClick(button, Qt.MouseButton.LeftButton, pos=button.rect().center())
                self.assert_action_response(button.text())

    def test_actions_images_real_timing_and_exact_status_changes(self):
        original_position = self.pet.pos()
        original_rect = self.pet.cat_label.geometry()
        original_size = self.pet.size()
        expected = {'Feed': (90, 70, 75), 'Pat': (90, 85, 75), 'Play': (85, 100, 60)}
        for action, values in expected.items():
            self.assertTrue(self.pet.perform_action(action))
            self.assertEqual(tuple(self.pet.status.values.values()), values)
            self.assertEqual(self.pet._asset_path.name, f'cat_{action.lower()}.png')
            self.assertEqual(self.pet.cat_label.pixmap().toImage(), self.pet.sprites.frame(action, self.pet.IMAGE_SIZE).toImage())
            self.assertEqual(self.pet.cat_label.geometry(), original_rect)
            self.assertEqual(self.pet.pos(), original_position)
            self.assertEqual(self.pet.size(), original_size)
            self.assertEqual(self.pet.message.text(), self.pet.ACTIONS[action][1])
            QTest.qWait(400)
            self.assertEqual(self.pet.current_state, action)
            self.assertGreater(self.pet.cat_label.progress, 0)
            self.assertTrue(self.pet.effects.items)
            self.assertFalse(self.pet.resize_handle.isEnabled())
            QTest.qWait(self.pet.ACTIONS[action][0] - 250)
            self.assertEqual(self.pet.current_state, 'Idle')
            self.assertEqual(self.pet._asset_path.name, 'cat_idle.png')
            self.assertTrue(self.pet.message.isHidden())
            self.assertFalse(self.pet.effects.items)
            self.assertTrue(self.pet.resize_handle.isEnabled())
            self.assertTrue(all(button.isEnabled() for button in self.pet.menu.buttons.values()))
            self.assertEqual(self.pet.cat_label.pixmap().toImage(), self.pet.sprites.frame('Idle', self.pet.IMAGE_SIZE).toImage())
            self.assertEqual(self.pet.cat_label.geometry(), original_rect)

    def test_duplicate_clicks_are_ignored_and_status_updates_live(self):
        self.pet.perform_action('Status')
        self.assertEqual(self.pet.status.values, {'Fullness': 65, 'Happiness': 65, 'Energy': 75})
        self.pet.perform_action('Feed')
        self.pet.action_animation.setCurrentTime(500)
        values = dict(self.pet.status.values)
        for action in ('Feed', 'Pat', 'Play'):
            self.assertFalse(self.pet.perform_action(action))
            self.pet.menu.buttons[action].click()
            self.assertEqual(self.pet.status.values, values)
            self.assertEqual(self.pet.action_animation.currentTime(), 500)
        self.assertTrue(self.pet.perform_action('Status'))
        self.assertFalse(self.pet.status_panel.isVisible())
        self.pet.perform_action('Status')
        for name, value in values.items():
            self.assertEqual(self.pet.status_panel.bars[name].value(), value)
            self.assertEqual(self.pet.status_panel.percentages[name].text(), f'{value}%')
        self.assertFalse(self.pet.geometry().intersects(self.pet.status_panel.geometry()))
        self.pet.action_animation.setCurrentTime(2000)
        self.pet.perform_action('Pat')
        self.assertEqual(self.pet.status_panel.bars['Happiness'].value(), 85)

    def test_status_clamps_at_both_limits(self):
        for action in ('Feed', 'Play', 'Pat', 'Feed'):
            for _ in range(120):
                self.pet.status.apply(action)
                self.assertTrue(all(0 <= value <= 100 for value in self.pet.status.values.values()))
        self.assertEqual(self.pet.status.values, {'Fullness': 100, 'Happiness': 100, 'Energy': 0})

    def test_effects_move_and_fish_disappears(self):
        self.pet.perform_action('Feed')
        self.pet.action_animation.setCurrentTime(200)
        start = self.pet.effects.items[0][0]
        self.pet.action_animation.setCurrentTime(900)
        later = self.pet.effects.items[0][0]
        self.assertGreater(later.center().x(), start.center().x())
        self.assertLess(later.width(), start.width())
        self.pet.action_animation.setCurrentTime(1400)
        self.assertEqual(self.pet.current_state, 'Feed')
        self.assertFalse(self.pet.effects.items)
        self.pet.action_animation.setCurrentTime(2000)
        self.pet.perform_action('Pat')
        self.pet.action_animation.setCurrentTime(300)
        first_y = self.pet.effects.items[0][0].y()
        self.pet.action_animation.setCurrentTime(800)
        self.assertLess(self.pet.effects.items[0][0].y(), first_y)
        self.pet.action_animation.setCurrentTime(2000)
        self.pet.perform_action('Play')
        self.pet.action_animation.setCurrentTime(150)
        first_x = self.pet.effects.items[0][0].x()
        self.pet.action_animation.setCurrentTime(450)
        self.assertNotEqual(self.pet.effects.items[0][0].x(), first_x)
        self.assertFalse(self.pet.cat_label.frame_transform().isIdentity())

    def test_missing_action_asset_has_clear_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            idle = Path(temporary) / 'cat_idle.png'
            shutil.copy2(self.pet.sprites.paths['Idle'], idle)
            with self.assertRaisesRegex(FileNotFoundError, 'cat_feed.png'):
                SpriteLibrary(idle)

    def test_chat_bubble_is_above_cat_and_follows_drag(self):
        self.open_menu()
        self.pet.perform_action('Play')
        cat = self.pet.cat_label.geometry().translated(self.pet.pos())
        bubble = self.pet.message.geometry()
        self.assertLess(bubble.center().x(), cat.center().x())
        self.assertLess(bubble.bottom(), cat.top())
        self.assertFalse(bubble.intersects(cat))
        for button in self.pet.menu.buttons.values():
            self.assertFalse(bubble.intersects(button.geometry().translated(self.pet.pos())))
        self.assertTrue(self.pet.message.windowFlags() & Qt.WindowType.WindowTransparentForInput)
        before = self.pet.message.pos()
        self.pet.move(self.pet.pos() - QPoint(15, 15))
        self.app.processEvents()
        self.assertEqual(self.pet.message.pos(), before - QPoint(15, 15))
        self.pet.action_animation.setCurrentTime(3000)
        self.assertTrue(self.pet.message.isHidden())

    def test_scaled_actions_keep_geometry_and_restore_size(self):
        self.pet.set_cat_scale(125)
        geometry = self.pet.cat_label.geometry()
        position = self.pet.pos()
        for action in ('Feed', 'Pat', 'Play'):
            self.pet.perform_action(action)
            self.assertEqual(self.pet.cat_label.geometry(), geometry)
            self.assertEqual(self.pet.pos(), position)
            self.pet.action_animation.setCurrentTime(self.pet.ACTIONS[action][0])
            self.assertEqual(self.pet.cat_scale, 125)
            self.assertEqual(self.pet.cat_label.geometry(), geometry)

    def test_drag_during_action_and_owned_panel_cleanup(self):
        self.pet.move(self.app.primaryScreen().availableGeometry().topLeft() + QPoint(20, 20))
        self.pet.perform_action('Play')
        self.pet.action_animation.setCurrentTime(250)
        start = self.pet.pos()
        local = self.pet.cat_label.geometry().center()
        QTest.mousePress(self.pet, Qt.MouseButton.LeftButton, pos=local)
        self.assertIsNotNone(self.pet._drag_offset)
        movement = QMouseEvent(QEvent.Type.MouseMove, QPointF(local), QPointF(start + local + QPoint(25, 15)), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(self.pet, movement)
        self.assertEqual(self.pet.pos(), start + QPoint(25, 15))
        QTest.mouseRelease(self.pet, Qt.MouseButton.LeftButton, pos=local)
        self.assertEqual(self.pet.current_state, 'Play')
        self.pet.perform_action('Status')
        self.pet.close()
        self.assertFalse(self.pet.status_panel.isVisible())

    def test_status_panel_stays_beside_menu_at_screen_edges(self):
        area = self.app.primaryScreen().availableGeometry()
        for point in (area.topLeft(), area.topRight(), area.bottomLeft(), area.bottomRight(), area.center()):
            self.pet.status_panel.close()
            self.pet._keep_on_screen(point)
            self.pet.perform_action('Status')
            self.assertFalse(self.pet.geometry().intersects(self.pet.status_panel.geometry()))
            self.assertTrue(area.contains(self.pet.status_panel.geometry()))
            self.assertTrue(area.contains(self.pet.geometry()))
            self.pet._keep_on_screen(self.pet.pos() + QPoint(15, 10))
            self.assertFalse(self.pet.geometry().intersects(self.pet.status_panel.geometry()))
            self.assertTrue(area.contains(self.pet.status_panel.geometry()))

    def test_status_toggle_remains_responsive_and_does_not_move_pet_repeatedly(self):
        self.pet.perform_action('Status')
        settled = self.pet.pos()
        ticks = []
        heartbeat = QTimer()
        heartbeat.setInterval(5)
        heartbeat.timeout.connect(lambda: ticks.append(True))
        heartbeat.start()
        for _ in range(12):
            self.pet.perform_action('Status')
            self.assertFalse(self.pet.status_panel.isVisible())
            self.pet.perform_action('Status')
            self.assertTrue(self.pet.status_panel.isVisible())
            self.app.processEvents()
            self.assertEqual(self.pet.pos(), settled)
        QTest.qWait(80)
        heartbeat.stop()
        self.assertGreater(len(ticks), 2)

    def test_resize_handle_drag_scales_whole_menu_and_keeps_hover(self):
        self.open_menu()
        handle = self.pet.resize_handle
        anchor = self.pet.mapToGlobal(self.pet.menu.center.toPoint())
        original_width = self.pet.width()
        original_button = self.pet.menu.buttons['Feed'].width()
        original_offset = self.pet.menu.center.x() - self.pet.menu.centers['Pat'][0]
        local = handle.rect().center()
        start = handle.mapToGlobal(local)
        QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=local)
        self.assertTrue(handle.dragging)
        movement = QMouseEvent(QEvent.Type.MouseMove, QPointF(local), QPointF(start + QPoint(25, 25)), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(handle, movement)
        self.assertGreater(self.pet.cat_scale, 100)
        ratio = self.pet.cat_scale / 100
        self.assertAlmostEqual(self.pet.width() / original_width, ratio, places=2)
        self.assertAlmostEqual(self.pet.menu.buttons['Feed'].width() / original_button, ratio, places=2)
        self.assertAlmostEqual((self.pet.menu.center.x() - self.pet.menu.centers['Pat'][0]) / original_offset, ratio, places=2)
        self.assertLess((self.pet.mapToGlobal(self.pet.menu.center.toPoint()) - anchor).manhattanLength(), 3)
        self.assertIsNone(self.pet._drag_offset)
        self.point_at(QPoint(-20, -20))
        QTest.qWait(500)
        self.assertTrue(self.pet._menu_active)
        QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=handle.rect().center())
        self.assertFalse(handle.dragging)
        self.assertTrue(self.pet.rect().contains(handle.geometry()))
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(self.pet.geometry()))
        # Drag back inward to make the entire group smaller again.
        local = handle.rect().center()
        start = handle.mapToGlobal(local)
        previous = self.pet.cat_scale
        QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=local)
        movement = QMouseEvent(QEvent.Type.MouseMove, QPointF(local), QPointF(start - QPoint(20, 20)), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(handle, movement)
        QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=handle.rect().center())
        self.assertLess(self.pet.cat_scale, previous)

    def test_exit_context_menu(self):
        selected = []
        def choose_exit():
            menu = self.app.activePopupWidget()
            self.assertIsInstance(menu, QMenu)
            self.assertEqual(menu.actions()[0].text(), 'Exit')
            selected.append(True)
            menu.actions()[0].trigger()
        def open_context():
            QTimer.singleShot(30, choose_exit)
            self.pet.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(220, 236), self.pet.mapToGlobal(QPoint(220, 236))))
        QTimer.singleShot(0, open_context)
        watchdog = QTimer()
        watchdog.setSingleShot(True)
        watchdog.timeout.connect(lambda: self.app.exit(2))
        watchdog.start(2000)
        self.assertEqual(self.app.exec(), 0)
        watchdog.stop()
        self.assertTrue(selected)


if __name__ == '__main__':
    unittest.main()
