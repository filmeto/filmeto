"""Status count widget for displaying status with numeric count."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

from .plan_status_icon import StatusIconWidget


class StatusCountWidget(QWidget):
    """Status icon with numeric count."""

    def __init__(self, label: str, color: str, tooltip: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.icon = StatusIconWidget(label, color, size=12, parent=self)
        layout.addWidget(self.icon)

        self.count_label = QLabel("0", self)
        self.count_label.setStyleSheet("color: #d0d0d0; font-size: 12px;")
        layout.addWidget(self.count_label)

        self.setToolTip(tooltip)

    def set_count(self, value: int):
        self.count_label.setText(str(value))
