"""Canonical ViewModel module for server list QML."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Property, Signal, Slot


class ServerListLabelsViewModel(QObject):
    """Translatable strings exposed to QML (updated when language or data changes)."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._empty_text = ""
        self._no_description = ""
        self._plugin_prefix = ""
        self._enable = ""
        self._disable = ""
        self._edit = ""
        self._delete = ""
        self._status_line = ""

    emptyTextChanged = Signal()
    noDescriptionChanged = Signal()
    pluginPrefixChanged = Signal()
    enableChanged = Signal()
    disableChanged = Signal()
    editChanged = Signal()
    deleteTextChanged = Signal()
    statusLineChanged = Signal()

    @Property(str, notify=emptyTextChanged)
    def emptyText(self) -> str:
        return self._empty_text

    @Property(str, notify=noDescriptionChanged)
    def noDescription(self) -> str:
        return self._no_description

    @Property(str, notify=pluginPrefixChanged)
    def pluginPrefix(self) -> str:
        return self._plugin_prefix

    @Property(str, notify=enableChanged)
    def enable(self) -> str:
        return self._enable

    @Property(str, notify=disableChanged)
    def disable(self) -> str:
        return self._disable

    @Property(str, notify=editChanged)
    def edit(self) -> str:
        return self._edit

    @Property(str, notify=deleteTextChanged)
    def deleteText(self) -> str:
        return self._delete

    @Property(str, notify=statusLineChanged)
    def statusLine(self) -> str:
        return self._status_line

    def set_static_labels(
        self,
        *,
        empty_text: str,
        no_description: str,
        plugin_prefix: str,
        enable: str,
        disable: str,
        edit: str,
        delete_text: str,
    ) -> None:
        if self._empty_text != empty_text:
            self._empty_text = empty_text
            self.emptyTextChanged.emit()
        if self._no_description != no_description:
            self._no_description = no_description
            self.noDescriptionChanged.emit()
        if self._plugin_prefix != plugin_prefix:
            self._plugin_prefix = plugin_prefix
            self.pluginPrefixChanged.emit()
        if self._enable != enable:
            self._enable = enable
            self.enableChanged.emit()
        if self._disable != disable:
            self._disable = disable
            self.disableChanged.emit()
        if self._edit != edit:
            self._edit = edit
            self.editChanged.emit()
        if self._delete != delete_text:
            self._delete = delete_text
            self.deleteTextChanged.emit()

    def set_status_line(self, line: str) -> None:
        if self._status_line != line:
            self._status_line = line
            self.statusLineChanged.emit()


class ServerListActionsViewModel(QObject):
    """Actions ViewModel invoked by QML and forwarded as Qt signals."""

    editRequested = Signal(str)
    toggleRequested = Signal(str, bool)
    deleteRequested = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    @Slot(str)
    def request_edit(self, server_name: str) -> None:
        self.editRequested.emit(server_name)

    @Slot(str, bool)
    def request_toggle(self, server_name: str, enabled: bool) -> None:
        self.toggleRequested.emit(server_name, enabled)

    @Slot(str)
    def request_delete(self, server_name: str) -> None:
        self.deleteRequested.emit(server_name)


# Backward compatibility aliases
ServerListLabels = ServerListLabelsViewModel
ServerListBridge = ServerListActionsViewModel

__all__ = [
    "ServerListLabelsViewModel",
    "ServerListActionsViewModel",
    "ServerListLabels",
    "ServerListBridge",
]
