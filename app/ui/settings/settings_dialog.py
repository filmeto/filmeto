# -*- coding: utf-8 -*-
"""Settings dialog using the same CustomDialog chrome as server list."""

from PySide6.QtCore import Signal

from app.data.workspace import Workspace
from app.ui.dialog.custom_dialog import CustomDialog
from app.ui.settings.settings_widget import SettingsWidget
from utils.i18n_utils import tr


class SettingsDialog(CustomDialog):
    """Application settings in the unified custom dialog frame."""

    settings_changed = Signal()

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(parent)
        self.workspace = workspace

        self.setMinimumSize(900, 700)
        self.resize(900, 700)

        self.show_navigation_buttons(False)
        self.set_title(tr("全局设置"))

        self._settings_widget = SettingsWidget(workspace)
        self._settings_widget.settings_changed.connect(self.settings_changed.emit)
        self.setContentWidget(self._settings_widget)

        self.add_button(tr("关闭"), self.reject, role="reject")
