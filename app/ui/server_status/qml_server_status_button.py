"""QML-based server status toolbar button (replaces QPainter + QPushButton)."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.server_status.server_status_qml_state import ServerStatusQmlState

logger = logging.getLogger(__name__)

_ICONFONT = Path(__file__).resolve().parents[3] / "textures" / "iconfont.ttf"


class ServerStatusButton(QWidget):
    """Toolbar control: icon + Server label + count badge; opens server dialog on click."""

    status_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("main_window_top_bar_button")
        self.setFixedSize(80, 32)
        self.setCursor(Qt.PointingHandCursor)

        self._state = ServerStatusQmlState(self)
        self._state.clicked.connect(self.status_clicked.emit)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setFocusPolicy(Qt.ClickFocus)
        self._quick.setAttribute(Qt.WA_AcceptTouchEvents, False)
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
