"""QML-backed members widget used by MembersPanel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QVBoxLayout, QWidget

from agent.crew import CrewMember, CrewTitle
from app.ui.base_widget import BaseWidget
from app.ui.panels.members.members_view_model import MembersListModel, MembersViewModel, _MemberRow
from utils.i18n_utils import tr

logger = logging.getLogger(__name__)


class QmlAgentChatMembersWidget(BaseWidget):
    """Members component API-compatible with legacy AgentChatMembersWidget."""

    member_selected = Signal(CrewMember)
    member_double_clicked = Signal(CrewMember)
    add_member_requested = Signal()

    def __init__(self, workspace, parent=None):
        super().__init__(workspace)
        if parent:
            self.setParent(parent)

        self._members_by_name: Dict[str, CrewMember] = {}
        self._active_members: set[str] = set()

        self._model = MembersListModel(self)
        self._view_model = MembersViewModel(self)
        self._view_model.memberClicked.connect(self._emit_member_selected)
        self._view_model.memberDoubleClicked.connect(self._emit_member_double_clicked)
        self._view_model.addMemberRequested.connect(self.add_member_requested.emit)

        self._quick = QQuickWidget(self)
        self._quick.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._quick.setAttribute(Qt.WA_TranslucentBackground, True)
        self._quick.setClearColor(Qt.transparent)
        self._quick.rootContext().setContextProperty("membersModel", self._model)
        self._quick.rootContext().setContextProperty("membersViewModel", self._view_model)

        qml_path = Path(__file__).resolve().parent.parent.parent / "qml" / "panels" / "MembersPanel.qml"
        self._quick.setSource(QUrl.fromLocalFile(str(qml_path)))
        if self._quick.status() == QQuickWidget.Error:
            for e in self._quick.errors():
                logger.error("MembersPanel QML error: %s", e.toString())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._quick)

        self._apply_texts()

    def refresh_texts(self) -> None:
        """Refresh i18n texts shown by QML toolbar."""
        self._apply_texts()

    def _apply_texts(self) -> None:
        self._view_model.set_texts(
            search_placeholder=tr("Search members..."),
            add_tooltip=tr("Add Member"),
        )

    def _member_to_row(self, member: CrewMember) -> _MemberRow:
        name = member.config.name or ""
        title = self._get_position_title(member)
        icon = member.config.icon or "A"
        color = member.config.color or "#4a90e2"
        lower = name.lower()
        return _MemberRow(
            key=lower,
            name=name.title(),
            title=title,
            icon=icon,
            color=color,
            active=lower in self._active_members,
            visible=True,
        )

    def _get_position_title(self, crew_member: CrewMember) -> str:
        crew_title_value = crew_member.config.metadata.get("crew_title") if crew_member.config.metadata else None
        if crew_title_value:
            title_instance = CrewTitle.create_from_title(crew_title_value)
            if title_instance and title_instance.title:
                return title_instance.get_title_display()
            return str(crew_title_value).replace("_", " ").title()

        raw_name = crew_member.config.name or ""
        try:
            title_instance = CrewTitle.create_from_title(raw_name.lower())
            if title_instance and title_instance.title:
                return title_instance.get_title_display()
        except Exception:
            pass
        return raw_name.title()

    def set_members(self, members: List[CrewMember]):
        self._members_by_name = {(m.config.name or "").lower(): m for m in members}
        rows = [self._member_to_row(m) for m in members]
        self._model.set_rows(rows)
        self._active_members = {n for n in self._active_members if n in self._members_by_name}

    def refresh_members(self):
        rows = []
        for lower_name, member in self._members_by_name.items():
            rows.append(self._member_to_row(member))
        self._model.set_rows(rows)

    def set_member_active(self, member_name: str, active: bool):
        lower_name = (member_name or "").lower()
        if active:
            self._active_members.add(lower_name)
        else:
            self._active_members.discard(lower_name)
        self._model.set_active(lower_name, active)

    def clear_all_active(self):
        self._active_members.clear()
        for lower_name in list(self._members_by_name.keys()):
            self._model.set_active(lower_name, False)

    def _emit_member_selected(self, member_key: str):
        member = self._members_by_name.get((member_key or "").lower())
        if member:
            self.member_selected.emit(member)

    def _emit_member_double_clicked(self, member_key: str):
        member = self._members_by_name.get((member_key or "").lower())
        if member:
            self.member_double_clicked.emit(member)
