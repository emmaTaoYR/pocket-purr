"""Session-only pet values and a small, owned floating Qt status panel."""

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget


class PetStatus(QObject):
    changed = Signal()
    DELTAS = {'Feed': (-25, 5, 0), 'Pat': (0, 15, 0), 'Play': (5, 20, -15)}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = {'Hunger': 35, 'Happiness': 65, 'Energy': 75}

    def apply(self, action: str) -> None:
        for key, delta in zip(self.values, self.DELTAS[action]):
            self.values[key] = max(0, min(100, self.values[key] + delta))
        self.changed.emit()


class StatusPanel(QWidget):
    """A separate tool window, so it never steals space from the radial menu."""

    def __init__(self, status: PetStatus, parent: QWidget):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('Pocket Kitty Status')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(248, 224)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(self)
        card.setObjectName('statusCard')
        card.setStyleSheet(
            '#statusCard { background: #fff8f5; border: 1px solid #e5d2e1; border-radius: 20px; }'
            'QLabel { color: #58475f; font: 10pt "Segoe UI"; border: none; }'
            'QPushButton { background: #f3e3ed; color: #725a78; border: none; border-radius: 11px; }'
            'QPushButton:hover { background: #e8cddf; }'
        )
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 16)
        layout.setSpacing(7)
        header = QHBoxLayout()
        header.addWidget(QLabel('Kitty Status', card))
        header.addStretch()
        self.close_button = QPushButton('\u00d7', card)
        self.close_button.setAccessibleName('Close status panel')
        self.close_button.setFixedSize(24, 24)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.close)
        header.addWidget(self.close_button)
        layout.addLayout(header)
        self.bars = {}
        self.percentages = {}
        for key, color in zip(status.values, ('#efba89', '#e9a5c6', '#a3d9c3')):
            row = QHBoxLayout()
            row.addWidget(QLabel(key, card))
            number = QLabel(card)
            number.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(number)
            layout.addLayout(row)
            bar = QProgressBar(card)
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            bar.setAccessibleName(key)
            bar.setStyleSheet(
                'QProgressBar { background: #efe8ec; border: none; border-radius: 5px; }'
                f'QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}'
            )
            layout.addWidget(bar)
            self.bars[key] = bar
            self.percentages[key] = number
        self.status = status
        status.changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        for key, value in self.status.values.items():
            self.bars[key].setValue(value)
            self.percentages[key].setText(f'{value}%')
