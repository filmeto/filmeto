"""
Server Status Button / Widget

ServerStatusButton is QML-backed.
ServerStatusWidget wraps it with periodic refresh from ServerManager.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QTimer, Signal, QUrl, Qt
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.base_widget import BaseWidget
from app.ui.server_status.server_status_view_model import ServerStatusViewModel
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)

_ICONFONT = Path(__file__).resolve().parents[3] / "textures" / "iconfont.ttf"


class ServerStatusButton(QWidget):
    """Toolbar control: icon + Server label + count badge; opens server dialog on click."""

    status_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("main_window_top_bar_button")
        # Must fit: left/right margins + icon + "Server" text + badge.
        self.setFixedSize(104, 32)
        self.setCursor(Qt.PointingHandCursor)

        self._state = ServerStatusViewModel(self)
        self._state.clicked.connect(self.status_clicked.emit)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setFocusPolicy(Qt.ClickFocus)
        self._quick.setAttribute(Qt.WA_AcceptTouchEvents, False)
        # Ensure QML can render rounded corners without showing a white clear-color.
        self._quick.setClearColor(Qt.transparent)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setStyleSheet("background: transparent; border: none;")

        qml_dir = Path(__file__).resolve().parent.parent / "qml" / "server_status"
        self._quick.engine().addImportPath(str(qml_dir.parent))

        qml_path = qml_dir / "ServerStatusButton.qml"
        self._quick.setSource(QUrl.fromLocalFile(str(qml_path)))

        root_obj = self._quick.rootObject()
        if root_obj is not None:
            root_obj.setProperty("viewState", self._state)
            if _ICONFONT.exists():
                root_obj.setProperty("iconFontSource", QUrl.fromLocalFile(str(_ICONFONT)))
        else:
            logger.error("ServerStatusButton QML root missing")

        if self._quick.status() == QQuickWidget.Error:
            for err in self._quick.errors():
                logger.error("ServerStatusButton QML: %s", err.toString())

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._quick)

    def set_server_counts(self, active: int, inactive: int) -> None:
        self._state.set_counts(active, inactive)

    def get_active_count(self) -> int:
        return self._state.get_active()

    def get_inactive_count(self) -> int:
        return self._state.get_inactive()


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
