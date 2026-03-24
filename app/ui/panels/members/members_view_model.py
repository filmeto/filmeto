"""ViewModel + model for QML members panel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt, Signal, Slot, QObject


@dataclass
class _MemberRow:
    key: str
    name: str
    title: str
    icon: str
    color: str
    active: bool
    visible: bool


class MembersListModel(QAbstractListModel):
    """Model exposed to QML for members list rendering."""

    NameRole = Qt.UserRole + 1
    KeyRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    IconRole = Qt.UserRole + 4
    ColorRole = Qt.UserRole + 5
    ActiveRole = Qt.UserRole + 6
    VisibleRole = Qt.UserRole + 7

    countChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._rows: List[_MemberRow] = []

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.KeyRole: b"key",
            self.TitleRole: b"title",
            self.IconRole: b"icon",
            self.ColorRole: b"color",
            self.ActiveRole: b"active",
            self.VisibleRole: b"visible",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == self.NameRole:
            return row.name
        if role == self.KeyRole:
            return row.key
        if role == self.TitleRole:
            return row.title
        if role == self.IconRole:
            return row.icon
        if role == self.ColorRole:
            return row.color
        if role == self.ActiveRole:
            return row.active
        if role == self.VisibleRole:
            return row.visible
        return None

    def set_rows(self, rows: List[_MemberRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.countChanged.emit()

    def set_active(self, lower_name: str, active: bool) -> None:
        for idx, row in enumerate(self._rows):
            if row.key == lower_name:
                if row.active != active:
                    row.active = active
                    mi = self.index(idx, 0)
                    self.dataChanged.emit(mi, mi, [self.ActiveRole])
                return

    @Slot(str)
    def set_filter(self, text: str) -> None:
        q = (text or "").strip().lower()
        changed_indexes: List[int] = []
        for i, row in enumerate(self._rows):
            visible = q in row.name.lower() if q else True
            if row.visible != visible:
                row.visible = visible
                changed_indexes.append(i)
        for i in changed_indexes:
            mi = self.index(i, 0)
            self.dataChanged.emit(mi, mi, [self.VisibleRole])


class MembersViewModel(QObject):
    """ViewModel with UI-facing actions/events for members panel."""

    searchPlaceholderChanged = Signal()
    addTooltipChanged = Signal()
    memberClicked = Signal(str)
    memberDoubleClicked = Signal(str)
    addMemberRequested = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._search_placeholder = ""
        self._add_tooltip = ""

    @Property(str, notify=searchPlaceholderChanged)
    def searchPlaceholder(self) -> str:
        return self._search_placeholder

    @Property(str, notify=addTooltipChanged)
    def addTooltip(self) -> str:
        return self._add_tooltip

    def set_texts(self, search_placeholder: str, add_tooltip: str) -> None:
        if self._search_placeholder != search_placeholder:
            self._search_placeholder = search_placeholder
            self.searchPlaceholderChanged.emit()
        if self._add_tooltip != add_tooltip:
            self._add_tooltip = add_tooltip
            self.addTooltipChanged.emit()

    @Slot(str)
    def on_member_clicked(self, member_name: str) -> None:
        self.memberClicked.emit(member_name)

    @Slot(str)
    def on_member_double_clicked(self, member_name: str) -> None:
        self.memberDoubleClicked.emit(member_name)

    @Slot()
    def on_add_member_clicked(self) -> None:
        self.addMemberRequested.emit()
