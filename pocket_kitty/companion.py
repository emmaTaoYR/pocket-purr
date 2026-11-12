"""Local idle motion and randomized speech scheduling. No network or threads."""

import math
import random

from PySide6.QtCore import QElapsedTimer, QObject, QTimer


class CompanionBehavior(QObject):
    NORMAL_INTERVAL = (180_000, 300_000)
    DEMO_INTERVAL = (15_000, 20_000)
    MESSAGES = (
        "I'm hungry... \U0001f41f", 'Can you pet me? \U0001f497',
        "Let's play! \U0001fab6", "You've been working so hard!",
        'Meow~', "Don't forget to take a break!", "I'm happy you're here!",
    )

    def __init__(self, pet, rng=None):
        super().__init__(pet)
        self.pet = pet
        self.rng = rng or random.Random()
        self.demo_mode = False
        self.stopped = False
        self.pending_random = False
        self.pending_confirmation = None
        self.last_message = None
        self.clock = QElapsedTimer()
        self.clock.start()
        self.next_float = self.rng.uniform(24, 40)
        self.float_started = None
        self.idle_timer = QTimer(self)
        self.idle_timer.setInterval(50)
        self.idle_timer.timeout.connect(self._idle_tick)
        self.message_timer = QTimer(self)
        self.message_timer.setSingleShot(True)
        self.message_timer.timeout.connect(self._message_due)
        self.bubble_timer = QTimer(self)
        self.bubble_timer.setSingleShot(True)
        self.bubble_timer.setInterval(4000)
        self.bubble_timer.timeout.connect(self._dismiss)
        self.idle_timer.start()
        self._schedule_next()

    def can_speak(self):
        return (not self.stopped and self.pet.current_state == 'Idle'
                and self.pet._drag_offset is None and not self.pet.resize_handle.dragging
                and not self.pet._context_menu_open)

    def _schedule_next(self):
        if not self.stopped:
            bounds = self.DEMO_INTERVAL if self.demo_mode else self.NORMAL_INTERVAL
            self.message_timer.start(self.rng.randint(*bounds))

    def set_demo_mode(self, enabled):
        if self.stopped:
            return
        self.demo_mode = bool(enabled)
        self.pending_random = False
        self.pending_confirmation = 'Demo Mode on - hello more often!' if enabled else 'Demo Mode off - quiet company.'
        self._schedule_next()
        self.on_available()

    def _message_due(self):
        self.message_timer.stop()
        if self.stopped:
            return
        self.pending_random = True
        self.on_available()
        if self.pending_random:
            # One pending message, not an accumulating queue of interruptions.
            self.message_timer.start(1000)

    def on_available(self):
        if not self.can_speak():
            return
        if self.pending_confirmation:
            text = self.pending_confirmation
            self.pending_confirmation = None
            self._show(text, 'confirmation')
        elif self.pending_random and self.pet.speech_kind is None:
            choices = [text for text in self.MESSAGES if text != self.last_message]
            text = self.rng.choice(choices)
            self.last_message = text
            self.pending_random = False
            self._show(text, 'ambient')
            self._schedule_next()

    def _show(self, text, kind):
        self.pet.show_speech(text, kind)
        self.bubble_timer.start(4000)

    def _dismiss(self):
        if self.pet.speech_kind in ('ambient', 'confirmation'):
            self.pet.hide_speech(animated=True)
        self.on_available()

    def action_started(self):
        # The action owns the shared bubble until its animation finishes.
        self.bubble_timer.stop()

    def _idle_tick(self):
        self.advance_idle(self.clock.elapsed() / 1000)

    def advance_idle(self, seconds):
        if self.stopped:
            return
        self.pet.cat_label.idle_seconds = seconds
        idle = self.pet.current_state == 'Idle' and self.pet._drag_offset is None and not self.pet.resize_handle.dragging
        if idle and self.float_started is None and seconds >= self.next_float:
            self.float_started = seconds
        amount = 0.0
        if self.float_started is not None:
            phase = (seconds - self.float_started) / 2.8
            if phase >= 1:
                self.float_started = None
                self.next_float = seconds + self.rng.uniform(24, 40)
            else:
                amount = math.sin(math.pi * max(0, phase)) ** 2
        self.pet.cat_label.float_amount = amount
        if not idle:
            return
        self.pet.cat_label.update()
        self.pet._cat_region = self.pet.cat_label.visual_region()
        self.pet._update_input_region()

    def stop(self):
        self.stopped = True
        self.idle_timer.stop()
        self.message_timer.stop()
        self.bubble_timer.stop()
        self.pending_random = False
        self.pending_confirmation = None
