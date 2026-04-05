# -*- coding: utf-8 -*-
"""Skeleton loading indicator: three blocks with a chasing highlight (painted, reliable)."""
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import QTimer, QSize, Qt
from PySide6.QtGui import QPainter, QColor, QBrush


class SkeletonBlocksPulseWidget(QWidget):
    """
    Three squares in a row; one block is highlighted at a time (rotating chase).
    Uses paintEvent so the flash is visible regardless of stylesheet inheritance.
    """

    _NUM_BLOCKS = 3

    def __init__(
        self,
        parent=None,
        block_size: int = 10,
        spacing: int = 6,
        interval_ms: int = 120,
    ):
        super().__init__(parent)
        self._block_size = block_size
        self._spacing = spacing
        self._phase = 0

        w = self._NUM_BLOCKS * block_size + (self._NUM_BLOCKS - 1) * spacing
        self.setFixedSize(w, block_size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._on_tick)

    def sizeHint(self) -> QSize:
        w = self._NUM_BLOCKS * self._block_size + (self._NUM_BLOCKS - 1) * self._spacing
        return QSize(w, self._block_size)

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _on_tick(self):
        self._phase = (self._phase + 1) % self._NUM_BLOCKS
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        dim = QColor(72, 76, 80, 160)
        bright = QColor(235, 238, 245, 255)

        for i in range(self._NUM_BLOCKS):
            c = bright if i == self._phase else dim
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.NoPen)
            x = i * (self._block_size + self._spacing)
            painter.drawRoundedRect(
                float(x),
                0.0,
                float(self._block_size),
                float(self._block_size),
                2.0,
                2.0,
            )
