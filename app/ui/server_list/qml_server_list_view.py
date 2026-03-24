"""QML-based server list (Qt Quick ListView + QAbstractListModel)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.ui.server_list.server_list_qml_bridge import ServerListBridge, ServerListLabels
from app.ui.server_list.server_list_qml_model import ServerListModel
from utils.i18n_utils import tr, translation_manager

if TYPE_CHECKING:
    from server.server import ServerManager

logger = logging.getLogger(__name__)

_DEFAULT_PROTECTED = frozenset({"local", "filmeto"})


class ServerListView(QWidget):
    """Server list using QML ListView for GPU-friendly scrolling and delegate reuse."""

    server_selected_for_edit = Signal(str)
    server_toggled = Signal(str, bool)
    server_deleted = Signal(str)
    add_server_clicked = Signal()
    refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server_manager: Optional["ServerManager"] = None

        self._model = ServerListModel(self)
        self._labels = ServerListLabels(self)
        self._bridge = ServerListBridge(self)

        self._bridge.editRequested.connect(self.server_selected_for_edit.emit)
        self._bridge.toggleRequested.connect(self.server_toggled.emit)
        self._bridge.deleteRequested.connect(self.server_deleted.emit)

        self._quick_widget = QQuickWidget(self)
        self._quick_widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick_widget.setFocusPolicy(Qt.ClickFocus)
        self._quick_widget.setAttribute(Qt.WA_AcceptTouchEvents, False)

        qml_dir = Path(__file__).resolve().parent.parent / "qml" / "server_list"
        self._quick_widget.engine().addImportPath(str(qml_dir.parent))

        qml_path = qml_dir / "ServerListView.qml"
        if not qml_path.exists():
            logger.error("Server list QML not found: %s", qml_path)
        self._quick_widget.setSource(QUrl.fromLocalFile(str(qml_path)))

        root_obj = self._quick_widget.rootObject()
        if root_obj is not None:
            root_obj.setProperty("serverRows", self._model)
            root_obj.setProperty("serverLabels", self._labels)
            root_obj.setProperty("serverBridge", self._bridge)
        else:
            logger.error("Server list QML root object missing")

        if self._quick_widget.status() == QQuickWidget.Error:
            for err in self._quick_widget.errors():
                logger.error("Server list QML error: %s", err.toString())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick_widget)

        translation_manager.language_changed.connect(self._on_language_changed)
        self._apply_static_labels()

    def _on_language_changed(self, _language_code: str) -> None:
        self._apply_static_labels()
        if self.server_manager:
            self.load_servers()

    def _apply_static_labels(self) -> None:
        self._labels.set_static_labels(
            empty_text=tr("暂无服务器配置"),
            no_description=tr("无描述"),
            plugin_prefix=tr("插件"),
            enable=tr("启用"),
            disable=tr("禁用"),
            edit=tr("编辑"),
            delete_text=tr("删除"),
        )

    def set_server_manager(self, server_manager: "ServerManager") -> None:
        self.server_manager = server_manager
        self.load_servers()

    def load_servers(self) -> None:
        if not self.server_manager:
            self._model.set_rows([])
            self._labels.set_status_line("")
            return

        servers = self.server_manager.list_servers()
        rows: List[dict] = []
        for server in servers:
            desc = server.config.description or ""
            rows.append(
                {
                    "name": server.name,
                    "server_type": server.server_type,
                    "description": desc,
                    "plugin_name": server.config.plugin_name,
                    "enabled": server.is_enabled,
                    "can_delete": server.name not in _DEFAULT_PROTECTED,
                }
            )

        self._model.set_rows(rows)

        active_count = sum(1 for s in servers if s.is_enabled)
        inactive_count = sum(1 for s in servers if not s.is_enabled)
        self._labels.set_status_line(
            f"{tr('总计')}: {len(servers)} | {tr('活跃')}: {active_count} | {tr('禁用')}: {inactive_count}"
        )
