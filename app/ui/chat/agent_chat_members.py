"""Agent chat members component implemented with QML."""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Signal

from agent.crew import CrewMember
from app.data.workspace import Workspace
from app.ui.panels.members.qml_members_widget import QmlAgentChatMembersWidget


class AgentChatMembersWidget(QmlAgentChatMembersWidget):
    """Backward-compatible alias using the QML members implementation."""

    member_selected = Signal(CrewMember)
    member_double_clicked = Signal(CrewMember)
    add_member_requested = Signal()

    def __init__(self, workspace: Workspace, parent=None):
        super().__init__(workspace, parent)
        self.members: List[CrewMember] = []
        self._selected_member: Optional[CrewMember] = None

        self.member_selected.connect(self._on_member_selected)

    def _on_member_selected(self, member: CrewMember) -> None:
        self._selected_member = member

    def set_members(self, members: List[CrewMember]):
        self.members = members
        super().set_members(members)

    def refresh_members(self):
        super().refresh_members()

    def get_selected_member(self) -> Optional[CrewMember]:
        return self._selected_member