"""Deterministic scheduling checks plus real short-timer and cleanup checks."""

import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from pathlib import Path
import unittest

from PySide6.QtCore import QPoint, QPointF, QAbstractAnimation, QTimer, QVariantAnimation
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pocket_kitty.companion import CompanionBehavior
from pocket_kitty.pet import PetWindow


class CompanionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.pet = PetWindow(Path(__file__).resolve().parents[1] / 'assets/cat_idle.png')
        self.pet.show()
        self.app.processEvents()
        self.behavior = self.pet.companion

    def tearDown(self):
        self.pet.close()
        self.pet.deleteLater()
        self.app.processEvents()

    def test_context_menu_demo_toggle_and_interval_ranges(self):
        self.assertFalse(self.behavior.demo_mode)
        self.assertTrue(180000 <= self.behavior.message_timer.interval() <= 300000)
        menu = self.pet.create_context_menu()
        demo = next(action for action in menu.actions() if action.text() == 'Demo Mode')
        self.assertTrue(demo.isCheckable())
        self.assertFalse(demo.isChecked())
        demo.trigger()
        self.assertTrue(self.behavior.demo_mode)
        self.assertIn('Demo Mode on', self.pet.message.text())
        self.assertEqual(self.pet.speech_kind, 'confirmation')
        for _ in range(12):
            self.behavior._schedule_next()
            self.assertTrue(15000 <= self.behavior.message_timer.interval() <= 20000)
        demo.trigger()
        self.assertFalse(self.behavior.demo_mode)
        self.assertIn('Demo Mode off', self.pet.message.text())
        self.assertTrue(180000 <= self.behavior.message_timer.interval() <= 300000)
        menu.deleteLater()

    def test_random_timer_and_real_four_second_bubble_lifetime(self):
        self.behavior.message_timer.start(10)
        QTest.qWait(70)
        self.assertEqual(self.pet.speech_kind, 'ambient')
        self.assertIn(self.pet.message.text(), CompanionBehavior.MESSAGES)
        self.assertTrue(self.pet.message.isVisible())
        self.assertEqual(self.behavior.bubble_timer.interval(), 4000)
        self.assertTrue(180000 <= self.behavior.message_timer.interval() <= 300000)
        QTest.qWait(3650)
        self.assertTrue(self.pet.message.isVisible())
        QTest.qWait(600)
        self.assertTrue(self.pet.message.isHidden())
        self.assertIsNone(self.pet.speech_kind)

    def test_random_speech_waits_for_every_action(self):
        for action in ('Feed', 'Pat', 'Play'):
            self.pet.perform_action(action)
            text = self.pet.message.text()
            self.behavior._message_due()
            self.assertTrue(self.behavior.pending_random)
            self.assertEqual(self.pet.speech_kind, 'action')
            self.assertEqual(self.pet.message.text(), text)
            self.behavior._dismiss()  # A stale timeout must not hide an action.
            self.assertEqual(self.pet.speech_kind, 'action')
            self.pet.action_animation.setCurrentTime(self.pet.ACTIONS[action][0])
            self.assertEqual(self.pet.current_state, 'Idle')
            self.assertEqual(self.pet.speech_kind, 'ambient')
            self.assertFalse(self.behavior.pending_random)
            self.pet.hide_speech()

    def test_messages_wait_for_drag_resize_and_context_menu(self):
        for attribute, blocked, unblocked in (('_drag_offset', QPoint(0, 0), None),
                                              ('_context_menu_open', True, False)):
            setattr(self.pet, attribute, blocked)
            self.behavior._message_due()
            self.assertTrue(self.behavior.pending_random)
            self.assertTrue(self.pet.message.isHidden())
            setattr(self.pet, attribute, unblocked)
            self.behavior.on_available()
            self.assertEqual(self.pet.speech_kind, 'ambient')
            self.pet.hide_speech()
        self.pet.resize_handle.dragging = True
        self.behavior._message_due()
        self.assertTrue(self.pet.message.isHidden())
        self.pet.resize_handle.dragging = False
        self.behavior.on_available()
        self.assertEqual(self.pet.speech_kind, 'ambient')

    def test_toggle_during_action_defers_confirmation_without_changing_status(self):
        self.pet.perform_action('Pat')
        values = dict(self.pet.status.values)
        self.behavior.set_demo_mode(True)
        self.assertEqual(self.pet.message.text(), self.pet.ACTIONS['Pat'][1])
        self.assertIsNotNone(self.behavior.pending_confirmation)
        self.pet.action_animation.setCurrentTime(2000)
        self.assertIn('Demo Mode on', self.pet.message.text())
        self.assertEqual(self.pet.speech_kind, 'confirmation')
        self.assertEqual(self.pet.status.values, values)
        self.behavior._message_due()
        self.assertEqual(self.pet.speech_kind, 'confirmation')
        self.behavior._dismiss()
        self.assertEqual(self.pet.speech_kind, 'ambient')
        self.behavior.set_demo_mode(False)
        self.assertFalse(self.behavior.pending_random)
        self.assertTrue(180000 <= self.behavior.message_timer.interval() <= 300000)

    def test_action_overrides_ambient_and_random_choices_do_not_repeat(self):
        self.behavior._message_due()
        previous = self.pet.message.text()
        self.pet.hide_speech()
        self.behavior._message_due()
        self.assertNotEqual(previous, self.pet.message.text())
        self.pet.perform_action('Feed')
        self.assertEqual(self.pet.speech_kind, 'action')
        self.assertFalse(self.behavior.bubble_timer.isActive())
        self.assertEqual(self.pet.message.text(), self.pet.ACTIONS['Feed'][1])

    def test_idle_motion_is_bounded_and_does_not_change_window_or_status(self):
        self.behavior.idle_timer.stop()
        position = self.pet.pos()
        geometry = self.pet.cat_label.geometry()
        values = dict(self.pet.status.values)
        point = QPointF(self.pet.cat_label.width() / 2, 0)
        for seconds in (0, 1.375, 2.75, 4.125):
            self.behavior.advance_idle(seconds)
            moved = self.pet.cat_label.frame_transform().map(point)
            self.assertLess(abs(moved.y() - point.y()), 1)
        self.behavior.next_float = 30
        self.behavior.advance_idle(30)
        self.behavior.advance_idle(31.4)
        self.assertAlmostEqual(self.pet.cat_label.float_amount, 1)
        self.assertLess(abs(self.pet.cat_label.frame_transform().map(point).y()), 4)
        self.behavior.advance_idle(33)
        self.assertEqual(self.pet.cat_label.float_amount, 0)
        self.assertGreater(self.behavior.next_float, 33)
        self.assertEqual(self.pet.pos(), position)
        self.assertEqual(self.pet.cat_label.geometry(), geometry)
        self.assertEqual(self.pet.status.values, values)

    def test_smooth_idle_action_transition(self):
        self.behavior.idle_timer.stop()
        self.behavior.advance_idle(1.375)
        idle_transform = self.pet.cat_label.frame_transform()
        self.pet.perform_action('Feed')
        self.pet.action_animation.pause()
        self.assertEqual(self.pet.cat_label.frame_transform(), idle_transform)
        self.assertEqual(self.pet.cat_label.action_blend(), 0)
        self.pet.action_animation.setCurrentTime(1000)
        self.assertEqual(self.pet.cat_label.action_blend(), 1)
        self.pet.action_animation.setCurrentTime(1999)
        self.assertLess(self.pet.cat_label.action_blend(), 0.001)
        self.pet.action_animation.stop()
        self.pet._finish_action()
        self.assertEqual(self.pet.cat_label.frame_transform(), idle_transform)

    def test_bubbles_fit_long_messages_and_screen_edges(self):
        area = self.app.primaryScreen().availableGeometry()
        for scale in (50, 100, 125):
            self.pet.set_cat_scale(scale)
            for corner in (area.topLeft(), area.topRight(), area.bottomLeft(), area.bottomRight()):
                self.pet.status_panel.close()
                self.pet._keep_on_screen(corner)
                self.pet._show_menu()
                self.pet.menu.animation.setCurrentTime(180)
                self.pet.perform_action('Status')
                self.pet.show_speech("Don't forget to take a break!", 'ambient')
                bubble = self.pet.message.geometry()
                self.assertTrue(area.contains(bubble))
                cat = self.pet.cat_label.geometry().translated(self.pet.pos())
                self.assertFalse(bubble.intersects(cat))
                self.assertFalse(bubble.intersects(self.pet.status_panel.geometry()))
                for button in self.pet.menu.buttons.values():
                    self.assertFalse(bubble.intersects(button.geometry().translated(self.pet.pos())))

    def test_shutdown_stops_all_timers_animations_and_owned_windows(self):
        self.pet.perform_action('Play')
        self.pet.perform_action('Status')
        self.behavior.set_demo_mode(True)
        self.pet.close()
        self.assertTrue(self.behavior.stopped)
        for timer in self.pet.findChildren(QTimer):
            self.assertFalse(timer.isActive())
        for animation in self.pet.findChildren(QVariantAnimation):
            self.assertEqual(animation.state(), QAbstractAnimation.State.Stopped)
        self.assertTrue(self.pet.message.isHidden())
        self.assertFalse(self.pet.status_panel.isVisible())
        seconds = self.pet.cat_label.idle_seconds
        self.behavior.set_demo_mode(True)
        QTest.qWait(100)
        self.assertEqual(self.pet.cat_label.idle_seconds, seconds)
        self.assertFalse(self.behavior.message_timer.isActive())


if __name__ == '__main__':
    unittest.main()
