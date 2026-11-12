"""Start Pocket Kitty: python main.py."""

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from pocket_kitty.pet import PetWindow
from pocket_kitty.lifecycle import ConsoleShutdown, instance_lock


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pocket Kitty")
    lock = instance_lock(Path(__file__).resolve().parent)
    if not lock.tryLock(0):
        print('Pocket Kitty is already running. Right-click the existing cat > Exit before restarting.', flush=True)
        return 0
    shutdown = ConsoleShutdown(app)
    try:
        return run_pet(app)
    finally:
        shutdown.close()
        lock.unlock()


def run_pet(app: QApplication) -> int:
    asset_path = Path(__file__).resolve().parent / "assets" / "cat_idle.png"
    try:
        kitty = PetWindow(asset_path)
    except (FileNotFoundError, ValueError) as error:
        print(f"Pocket Kitty: {error}", file=sys.stderr)
        QMessageBox.critical(None, "Pocket Kitty — image error", str(error))
        return 1

    kitty.show()
    print('Pocket Kitty is running. Hover to resize. Right-click > Exit, or press Ctrl+C here to quit.', flush=True)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
