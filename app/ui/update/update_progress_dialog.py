"""
Update Progress Dialog

Shows download progress and handles installation after download completes.
"""

import logging
from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QWidget, QProgressBar
)
from PySide6.QtCore import Qt, QTimer

from app.ui.dialog.custom_dialog import CustomDialog
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class UpdateProgressDialog(CustomDialog):
    """Modal dialog showing download progress with cancel support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(450, 200)
        self.resize(450, 200)

        self.set_title(tr("正在更新"))
        self._cancel_flag = type("CancelFlag", (), {"is_set": False})()

        self._init_ui()

    @property
    def cancel_flag(self):
        return self._cancel_flag

    def _init_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Status label
        self.status_label = QLabel(tr("正在下载更新..."))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Detail label (bytes transferred)
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(self.detail_label)

        layout.addStretch()

        self.setContentWidget(container)

        # Cancel button
        self._cancel_button = self.add_button(tr("取消"), self._on_cancel_clicked, role="reject")

    def update_progress(self, downloaded: int, total: int):
        """Update the progress bar with current download state."""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_bar.setValue(percent)
            self.detail_label.setText(
                f"{_format_bytes(downloaded)} / {_format_bytes(total)}"
            )

    def set_status(self, text: str):
        """Update the status label text."""
        self.status_label.setText(text)

    def set_installing(self):
        """Switch UI to 'installing' state."""
        self.set_status(tr("正在安装更新..."))
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.detail_label.setText("")
        self._cancel_button.setEnabled(False)

    def set_error(self, message: str):
        """Show an error state."""
        self.set_status(tr("更新失败"))
        self.detail_label.setText(message)
        self.detail_label.setStyleSheet("font-size: 11px; color: #F44336;")

    def _on_cancel_clicked(self):
        self._cancel_flag.is_set = True
        self.set_status(tr("正在取消..."))
        self._cancel_button.setEnabled(False)


def _format_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
