"""ViewModel + model for QML actor panel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt, Signal, Slot, QObject


@dataclass
class _ActorRow:
    name: str
    description: str
    image_path: str
    selected: bool


class ActorListModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    DescriptionRole = Qt.UserRole + 2
    ImagePathRole = Qt.UserRole + 3
    SelectedRole = Qt.UserRole + 4

    countChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._rows: List[_ActorRow] = []

    @Property(int, notify=countChanged)
    def count(self) -> int:
        return len(self._rows)

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.DescriptionRole: b"description",
            self.ImagePathRole: b"imagePath",
            self.SelectedRole: b"selected",
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
        if role == self.DescriptionRole:
            return row.description
        if role == self.ImagePathRole:
            return row.image_path
        if role == self.SelectedRole:
            return row.selected
        return None

    def set_rows(self, rows: List[_ActorRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.countChanged.emit()

    def set_selected_by_name(self, name: str, selected: bool) -> None:
        for idx, row in enumerate(self._rows):
            if row.name == name:
                if row.selected != selected:
                    row.selected = selected
                    mi = self.index(idx, 0)
                    self.dataChanged.emit(mi, mi, [self.SelectedRole])
                return


class ActorPanelViewModel(QObject):
    emptyMessageChanged = Signal()
    addRequested = Signal()
    drawRequested = Signal()
    extractRequested = Signal()
    actorClicked = Signal(str)
    actorDoubleClicked = Signal(str)
    actorSelectionChanged = Signal(str, bool)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._empty_message = ""

    @Property(str, notify=emptyMessageChanged)
    def emptyMessage(self) -> str:
        return self._empty_message

    def set_empty_message(self, message: str) -> None:
        if self._empty_message != message:
            self._empty_message = message
            self.emptyMessageChanged.emit()

    @Slot()
    def on_add_clicked(self) -> None:
        self.addRequested.emit()

    @Slot()
    def on_draw_clicked(self) -> None:
        self.drawRequested.emit()

    @Slot()
    def on_extract_clicked(self) -> None:
        self.extractRequested.emit()

    @Slot(str)
    def on_actor_clicked(self, name: str) -> None:
        self.actorClicked.emit(name)

    @Slot(str)
    def on_actor_double_clicked(self, name: str) -> None:
        self.actorDoubleClicked.emit(name)

    @Slot(str, bool)
    def on_actor_selection_changed(self, name: str, selected: bool) -> None:
        self.actorSelectionChanged.emit(name, selected)
