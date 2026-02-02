"""Clickable frame widget that emits a signal when clicked."""

from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, Signal


class ClickableFrame(QFrame):
    """Frame that emits clicked signal on mouse press."""

    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
