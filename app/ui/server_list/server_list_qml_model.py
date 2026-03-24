"""QAbstractListModel for server list QML view (virtualized ListView)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt, Signal


class ServerListModel(QAbstractListModel):
    """Exposes server rows to QML with role names for delegate bindings."""

    countChanged = Signal()

    NameRole = Qt.UserRole + 1
    ServerTypeRole = Qt.UserRole + 2
    DescriptionRole = Qt.UserRole + 3
    PluginNameRole = Qt.UserRole + 4
    EnabledRole = Qt.UserRole + 5
    CanDeleteRole = Qt.UserRole + 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict[str, Any]] = []

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == self.NameRole:
            return row.get("name", "")
        if role == self.ServerTypeRole:
            return row.get("server_type", "")
        if role == self.DescriptionRole:
            return row.get("description", "")
        if role == self.PluginNameRole:
            return row.get("plugin_name", "")
        if role == self.EnabledRole:
            return bool(row.get("enabled", True))
        if role == self.CanDeleteRole:
            return bool(row.get("can_delete", True))
        return None

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.ServerTypeRole: b"serverType",
            self.DescriptionRole: b"description",
            self.PluginNameRole: b"pluginName",
            self.EnabledRole: b"enabled",
            self.CanDeleteRole: b"canDelete",
        }

    def set_rows(self, rows: List[Dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()
        self.countChanged.emit()
