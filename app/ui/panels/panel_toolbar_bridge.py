"""Bridge model for QML panel toolbar title and actions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot


@dataclass
class _ActionState:
    action_id: str
    icon_text: str
    tooltip: str
    enabled: bool = True
    visible: bool = True


class ToolbarActionHandle:
    """Handle returned by BasePanel.add_toolbar_button for runtime updates."""

    def __init__(self, view_model: "PanelToolbarViewModel", action_id: str):
        self._view_model = view_model
        self._action_id = action_id

    @property
    def action_id(self) -> str:
        return self._action_id

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - Qt-style API compatibility
        self._view_model.set_action_enabled(self._action_id, enabled)

    def setVisible(self, visible: bool) -> None:  # noqa: N802 - Qt-style API compatibility
        self._view_model.set_action_visible(self._action_id, visible)

    def setToolTip(self, tooltip: str) -> None:  # noqa: N802 - Qt-style API compatibility
        self._view_model.set_action_tooltip(self._action_id, tooltip)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-style API compatibility
        self._view_model.set_action_text(self._action_id, text)


class PanelToolbarViewModel(QObject):
    """ViewModel for panel toolbar QML."""

    titleChanged = Signal()
    actionsChanged = Signal()
    actionInvoked = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._title = ""
        self._actions: Dict[str, _ActionState] = {}
        self._order: list[str] = []
        self._seq = 0

    @Property(str, notify=titleChanged)
    def title(self) -> str:
        return self._title

    def set_title(self, title: str) -> None:
        if self._title != title:
            self._title = title
            self.titleChanged.emit()

    @Property("QVariantList", notify=actionsChanged)
    def actions(self):
        rows = []
        for aid in self._order:
            row = self._actions.get(aid)
            if not row:
                continue
            rows.append(
                {
                    "id": row.action_id,
                    "iconText": row.icon_text,
                    "tooltip": row.tooltip,
                    "enabled": row.enabled,
                    "visible": row.visible,
                }
            )
        return rows

    def add_action(self, icon_text: str, tooltip: str = "") -> ToolbarActionHandle:
        self._seq += 1
        aid = f"panel_action_{self._seq}"
        self._actions[aid] = _ActionState(aid, icon_text, tooltip)
        self._order.append(aid)
        self.actionsChanged.emit()
        return ToolbarActionHandle(self, aid)

    def set_action_enabled(self, action_id: str, enabled: bool) -> None:
        row = self._actions.get(action_id)
        if row and row.enabled != enabled:
            row.enabled = enabled
            self.actionsChanged.emit()

    def set_action_visible(self, action_id: str, visible: bool) -> None:
        row = self._actions.get(action_id)
        if row and row.visible != visible:
            row.visible = visible
            self.actionsChanged.emit()

    def set_action_tooltip(self, action_id: str, tooltip: str) -> None:
        row = self._actions.get(action_id)
        if row and row.tooltip != tooltip:
            row.tooltip = tooltip
            self.actionsChanged.emit()

    def set_action_text(self, action_id: str, icon_text: str) -> None:
        row = self._actions.get(action_id)
        if row and row.icon_text != icon_text:
            row.icon_text = icon_text
            self.actionsChanged.emit()

    @Slot(str)
    def invoke_action(self, action_id: str) -> None:
        self.actionInvoked.emit(action_id)


# Backward compatibility alias
PanelToolbarBridge = PanelToolbarViewModel
