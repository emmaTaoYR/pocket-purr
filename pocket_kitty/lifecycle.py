"""Local single-instance lock and clean console shutdown for Qt."""

import hashlib
from pathlib import Path
import signal
import tempfile

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication


def instance_lock(project: Path) -> QLockFile:
    # Each checkout gets its own local lock; no sockets, server, or network.
    key = hashlib.sha256(str(project.resolve()).casefold().encode('utf-8')).hexdigest()[:16]
    lock = QLockFile(str(Path(tempfile.gettempdir()) / f'pocket-kitty-{key}.lock'))
    lock.setStaleLockTime(0)
    return lock


class ConsoleShutdown:
    """Convert Ctrl+C/Ctrl+Break into app.quit instead of KeyboardInterrupt."""

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self._previous = {}
        for name in ('SIGINT', 'SIGBREAK'):
            signum = getattr(signal, name, None)
            if signum is not None:
                self._previous[signum] = signal.signal(signum, self._quit)
        # Python checks pending console signals when it regains control from
        # Qt. A small timer ensures this also happens while the pet is idle.
        self.timer = QTimer(app)
        self.timer.setInterval(100)
        self.timer.timeout.connect(lambda: None)
        self.timer.start()

    def _quit(self, signum, frame) -> None:
        self.app.quit()

    def close(self) -> None:
        self.timer.stop()
        self.timer.deleteLater()
        for signum, previous in self._previous.items():
            signal.signal(signum, previous)
