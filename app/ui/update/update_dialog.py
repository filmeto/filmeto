"""
Update Dialog

Displays available update information and initiates download/install.
"""

import logging
from PySide6.QtWidgets import (
    QLabel, QVBoxLayout, QTextEdit, QWidget
)
from PySide6.QtCore import Qt

from app.ui.dialog.custom_dialog import CustomDialog
from app.services.update_service import UpdateInfo
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class UpdateDialog(CustomDialog):
    """Dialog showing update information with option to download or skip."""

    def __init__(self, update_info: UpdateInfo, current_version: str, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.current_version = current_version

        self.setMinimumSize(500, 400)
        self.resize(500, 400)

        self.set_title(tr("发现新版本"))
        self._init_ui()

    def _init_ui(self):
        """Build the update information UI."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Version info
        version_label = QLabel(
            f"{tr('当前版本')}: {self.current_version}\n"
            f"{tr('最新版本')}: {self.update_info.version}"
        )
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(version_label)

        # Release notes header
        notes_header = QLabel(tr("更新说明"))
        notes_header.setStyleSheet("font-size: 13px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(notes_header)

        # Release notes content
        notes_edit = QTextEdit()
        notes_edit.setReadOnly(True)
        notes_edit.setPlainText(self.update_info.release_notes or tr("暂无更新说明"))
        notes_edit.setMaximumHeight(180)
        notes_edit.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; border: 1px solid #3c3c3c; "
            "border-radius: 4px; padding: 8px; color: #e0e0e0; }"
        )
        layout.addWidget(notes_edit)

        layout.addStretch()

        self.setContentWidget(container)

        # Dialog buttons
        if self.update_info.force_update:
            # Force update: only allow "Update Now"
            self.add_button(tr("立即更新"), self._on_update_clicked, role="accept")
        else:
            self.add_button_row([
                (tr("以后再说"), self._on_later_clicked, "reject"),
                (tr("跳过此版本"), self._on_skip_clicked, "reject"),
                (tr("立即更新"), self._on_update_clicked, "accept"),
            ])

    def _on_update_clicked(self):
        self.accept()

    def _on_later_clicked(self):
        self.reject()

    def _on_skip_clicked(self):
        # Return a special result to indicate "skip this version"
        self.done(2)  # Use result code 2 for "skip"
