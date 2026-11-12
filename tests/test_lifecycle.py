"""Exercise the actual entry point in isolated local processes."""

import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest


class ApplicationLifecycle(unittest.TestCase):
    def test_console_interrupt_and_duplicate_launch(self):
        source = Path(__file__).resolve().parents[1]
        temporary = tempfile.TemporaryDirectory(prefix='pocket-kitty-test-')
        self.addCleanup(temporary.cleanup)
        project = Path(temporary.name)
        shutil.copy2(source / 'main.py', project / 'main.py')
        shutil.copytree(source / 'pocket_kitty', project / 'pocket_kitty', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(source / 'assets', project / 'assets')
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
        # Raise the same SIGINT Python receives for Ctrl+C while Qt is idle.
        # Using a timer avoids sending console events to the test runner's group.
        code = '''
import signal
from PySide6.QtCore import QTimer
import main
original = main.run_pet
def run(app):
    QTimer.singleShot(2500, lambda: signal.raise_signal(signal.SIGINT))
    return original(app)
main.run_pet = run
raise SystemExit(main.main())
'''
        child = subprocess.Popen([sys.executable, '-c', code], cwd=project, env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = queue.Queue()
        thread = threading.Thread(target=lambda: ready.put(child.stdout.readline()), daemon=True)
        thread.start()
        try:
            self.assertIn('Pocket Kitty is running.', ready.get(timeout=8))
            duplicate = subprocess.run([sys.executable, 'main.py'], cwd=project, env=env,
                                       capture_output=True, text=True, timeout=8)
            self.assertEqual(duplicate.returncode, 0, duplicate.stderr)
            self.assertIn('already running', duplicate.stdout)
            stdout, stderr = child.communicate(timeout=8)
            self.assertEqual(child.returncode, 0, stderr)
            self.assertNotIn('KeyboardInterrupt', stderr)
            # A clean exit releases the lock, so another launch works too.
            again = subprocess.run([sys.executable, '-c', code], cwd=project, env=env,
                                   capture_output=True, text=True, timeout=8)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertIn('Pocket Kitty is running.', again.stdout)
            self.assertNotIn('KeyboardInterrupt', again.stderr)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
