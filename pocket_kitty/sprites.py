"""Align existing PNGs at runtime; source image files remain untouched."""

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap


class SpriteLibrary:
    # Manually measured body anchors: center X, ear top, paw baseline.
    # Decorative hearts, fish, and feathers do not determine the body's scale.
    ANCHORS = {'Feed': (630, 164, 1030), 'Pat': (650, 114, 1060), 'Play': (620, 72, 1105)}

    def __init__(self, idle_path: Path):
        self.paths = {'Idle': idle_path, **{key: idle_path.parent / f'cat_{key.lower()}.png' for key in self.ANCHORS}}
        self.originals = {}
        self.cache = {}
        for state, path in self.paths.items():
            if not path.is_file():
                raise FileNotFoundError(f'Cat image is missing:\n{path}\n\nRestore assets/{path.name}, then restart.')
            image = QPixmap(str(path))
            if image.isNull():
                raise ValueError(f'Cannot read the cat image:\n{path}\n\nUse a valid PNG file.')
            self.originals[state] = image

    def frame(self, state: str, maximum: QSize) -> QPixmap:
        key = (state, maximum.width(), maximum.height())
        if key in self.cache:
            return self.cache[key]
        idle = self.originals['Idle'].scaled(maximum, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        if state == 'Idle':
            result = idle
        else:
            result = QPixmap(idle.size())
            result.fill(Qt.GlobalColor.transparent)
            center, top, feet = self.ANCHORS[state]
            # Use the idle artwork's proportions as the shared visual reference.
            baseline = idle.height() * 1235 / 1302
            body_height = idle.height() * (1235 - 120) / 1302
            scale = body_height / (feet - top)
            source = self.originals[state]
            destination = QRectF(idle.width() * 0.52 - center * scale,
                                 baseline - feet * scale,
                                 source.width() * scale, source.height() * scale)
            painter = QPainter(result)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawPixmap(destination, source, QRectF(source.rect()))
            painter.end()
        # Bound memory even if the resize handle visits every percentage.
        if len(self.cache) >= 24:
            self.cache.clear()
        self.cache[key] = result
        return result
