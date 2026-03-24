"""
Server Status Button / Widget

ServerStatusButton is QML-backed (see qml_server_status_button.py).
ServerStatusWidget wraps it with periodic refresh from ServerManager.
"""

import logging

from PySide6.QtCore import QTimer, Signal

from app.ui.base_widget import BaseWidget
from app.ui.server_status.qml_server_status_button import ServerStatusButton
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class ServerStatusWidget(BaseWidget):
    """
    Widget wrapper for ServerStatusButton with auto-refresh capability.
    Integrates with ServerManager to fetch and display real-time status.
    """

    show_status_dialog = Signal()

    def __init__(self, workspace):
        super().__init__(workspace)

        self.status_button = ServerStatusButton(self)
        self.status_button.setToolTip(tr("服务器管理"))
        self.status_button.status_clicked.connect(self._on_button_clicked)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_status)
        self.refresh_timer.start(5000)

        self._refresh_status()

    def _on_button_clicked(self):
        self.show_status_dialog.emit()

    def _refresh_status(self):
        try:
            from server.server import ServerManager

            workspace_path = self.workspace.workspace_path
            server_manager = ServerManager(workspace_path)

            servers = server_manager.list_servers()
            active_count = sum(1 for s in servers if s.is_enabled)
            inactive_count = sum(1 for s in servers if not s.is_enabled)

            self.status_button.set_server_counts(active_count, inactive_count)

        except Exception as e:
            logger.error(f"Failed to refresh server status: {e}")
            self.status_button.set_server_counts(0, 0)

    def force_refresh(self):
        self._refresh_status()
