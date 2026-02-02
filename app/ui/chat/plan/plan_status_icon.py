"""Status icon widget for displaying circular status indicators."""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor, QPainter, QFont, QPen


class StatusIconWidget(QWidget):
    """Small circular status icon with text."""

    def __init__(self, text: str, color: str, size: int = 14, parent=None):
        super().__init__(parent)
        self._text = text
        self._color = QColor(color)
        self._size = size
        self.setFixedSize(size, size)

    def set_style(self, text: str, color: str):
        self._text = text
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.setBrush(self._color)
        painter.setPen(QPen(self._color))
        painter.drawEllipse(rect)

        font = QFont()
        font.setPointSize(max(7, self._size // 2))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(rect, Qt.AlignCenter, self._text)
